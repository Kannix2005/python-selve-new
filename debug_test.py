malformed_xml = '<?xml version="1.0"? encoding="UTF-8"?><methodResponse><array><string>test</string></array></methodResponse>'
print("Original:", repr(malformed_xml))

corrected_xml = str(malformed_xml).replace('<?xml version="1.0"? encoding="UTF-8">', '<?xml version="1.0" encoding="UTF-8"?>')
print("Corrected:", repr(corrected_xml))

print("Contains correct header:", '<?xml version="1.0" encoding="UTF-8"?>' in corrected_xml)
print("Contains malformed header:", '<?xml version="1.0"? encoding="UTF-8"?>' in corrected_xml)
