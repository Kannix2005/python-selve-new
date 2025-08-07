test = '<?xml version="1.0"? encoding="UTF-8"?><test></test>'
replaced = test.replace('<?xml version="1.0"? encoding="UTF-8"?>', '<?xml version="1.0" encoding="UTF-8"?>')
print('Original:', repr(test))
print('Replaced:', repr(replaced))
print('Fixed contains correct header:', '<?xml version="1.0" encoding="UTF-8"?>' in replaced)
print('Original malformed still present:', '<?xml version="1.0"? encoding="UTF-8"?>' in replaced)
