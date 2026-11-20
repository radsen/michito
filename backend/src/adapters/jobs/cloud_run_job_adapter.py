"""
Michito Cloud Run Job Invocation Adapter.
Triggers ephemeral batch worker executions asynchronously via the GCP Cloud Run v2 REST API.
Decouples heavy compute (15-20 min) from the customer-facing Web API service (< 200ms).
"""

import os
import sys
import logging
import threading
from typing import Optional, Dict, Any

logger = logging.getLogger("CloudRunJobAdapter")


class CloudRunJobAdapter:
    def __init__(
        self,
        project_id: Optional[str] = None,
        region: Optional[str] = None,
        job_name: Optional[str] = None,
    ):
        self.project_id = (
            project_id
            or os.environ.get("GCP_PROJECT_ID")
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
            or "michito-staging"
        )
        self.region = region or os.environ.get("GCP_REGION") or "us-central1"
        self.job_name = job_name or os.environ.get("CLOUD_RUN_JOB_NAME") or "michito-batch-worker"
        self.environment = os.environ.get("ENVIRONMENT", "local").lower()

    def trigger_batch_harvesting_job(self, order_id: str) -> bool:
        """
        Asynchronously triggers the Cloud Run Job for the specified order_id.
        In staging/production: Dispatches via GCP Cloud Run v2 REST API with default credentials.
        In local/test: Dispatches via a background thread to prevent blocking.
        """
        if not order_id:
            logger.error("[CloudRunJobAdapter] Missing order_id to trigger job.")
            return False

        # If in local / test mode or explicit local flag set, run via background thread
        if self.environment in ("local", "dev", "test") or os.environ.get("USE_LOCAL_JOB_RUNNER") == "true":
            logger.info(f"[CloudRunJobAdapter] Local/Dev environment detected. Spawning background thread for `{order_id}`.")
            try:
                from src.entrypoints.workers.job_runner import run_batch_job
                thread = threading.Thread(
                    target=run_batch_job,
                    args=(order_id,),
                    daemon=True,
                    name=f"worker-{order_id}",
                )
                thread.start()
                return True
            except Exception as e:
                logger.error(f"[CloudRunJobAdapter] Failed to spawn local background thread for `{order_id}`: {e}")
                return False

        # In Staging / Production: Invoke GCP Cloud Run Job
        try:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession

            credentials, project = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            authed_session = AuthorizedSession(credentials)

            url = (
                f"https://run.googleapis.com/v2/projects/{self.project_id}/"
                f"locations/{self.region}/jobs/{self.job_name}:run"
            )

            payload = {
                "overrides": {
                    "containerOverrides": [
                        {
                            "args": ["-m", "src.entrypoints.workers.job_runner", "--order-id", order_id],
                            "env": [
                                {"name": "ORDER_ID", "value": order_id},
                            ],
                        }
                    ]
                }
            }

            logger.info(f"[CloudRunJobAdapter] Dispatching Cloud Run Job `{self.job_name}` for order `{order_id}`...")
            response = authed_session.post(url, json=payload, timeout=10.0)

            if response.status_code in (200, 202):
                res_data = response.json()
                execution_name = res_data.get("name", "unknown")
                logger.info(
                    f"[CloudRunJobAdapter] Successfully triggered Cloud Run Job execution: {execution_name} (HTTP {response.status_code})"
                )
                return True
            else:
                logger.error(
                    f"[CloudRunJobAdapter] Failed to trigger Cloud Run Job (HTTP {response.status_code}): {response.text}"
                )
                # Fallback to background thread if Cloud Run invocation fails
                logger.warning(f"[CloudRunJobAdapter] Falling back to background worker thread for `{order_id}`.")
                from src.entrypoints.workers.job_runner import run_batch_job
                thread = threading.Thread(
                    target=run_batch_job,
                    args=(order_id,),
                    daemon=True,
                    name=f"fallback-worker-{order_id}",
                )
                thread.start()
                return True

        except Exception as err:
            logger.error(f"[CloudRunJobAdapter] Exception invoking Cloud Run Job for `{order_id}`: {err}")
            # Resilient fallback to background thread so transaction is never lost
            try:
                from src.entrypoints.workers.job_runner import run_batch_job
                thread = threading.Thread(
                    target=run_batch_job,
                    args=(order_id,),
                    daemon=True,
                    name=f"resilient-worker-{order_id}",
                )
                thread.start()
                return True
            except Exception as thread_err:
                logger.error(f"[CloudRunJobAdapter] Fatal: Could not dispatch worker thread: {thread_err}")
                return False
