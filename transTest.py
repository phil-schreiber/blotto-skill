from google.cloud import translate_v2 as translate

text = 'Hallo Leute'
translate_client = translate.Client()

response = translate_client.translate(text, target_language='en', source_language='de')

print(response['translatedText'])
