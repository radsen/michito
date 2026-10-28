def calculate_check_digit(nit_str: str) -> int:
    weights = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
    total = 0
    for i, digit in enumerate(reversed(nit_str)):
        total += int(digit) * weights[i]
    rem = total % 11
    if rem > 1:
        return 11 - rem
    return rem

print(calculate_check_digit("800197268"))
print(calculate_check_digit("900353939"))
