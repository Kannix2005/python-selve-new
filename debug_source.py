# Copy the exact strings from source code
source_malformed = '<?xml version="1.0"? encoding="UTF-8"?>'
source_corrected = '<?xml version="1.0" encoding="UTF-8"?>'

test_xml = '<?xml version="1.0"? encoding="UTF-8"?><test></test>'

print("Source malformed:", repr(source_malformed))
print("Source corrected:", repr(source_corrected))
print("Test XML:", repr(test_xml))

result = test_xml.replace(source_malformed, source_corrected)
print("Result:", repr(result))

print("Contains corrected:", source_corrected in result)
print("Contains malformed:", source_malformed in result)
