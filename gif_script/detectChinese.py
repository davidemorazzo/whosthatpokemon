import regex as re

pattern = re.compile(r'([\p{IsHan}\p{IsBopo}\p{IsHira}\p{Katakana}]+)', re.UNICODE)
pattern = re.compile(r'\([^()]*\)', re.UNICODE)

input = u"(プテラ) is the 142nd P"
output = pattern.sub(r'', input)
print(output)