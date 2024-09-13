import base64
import zlib

async def compress_string(input_string):
    # Сжимаем строку с помощью zlib
    compressed_data = zlib.compress(input_string.encode('utf-8'))
    # Кодируем сжатые данные в Base64 для удобства хранения и передачи
    compressed_base64 = base64.b64encode(compressed_data)
    return compressed_base64.decode('utf-8')

async def decompress_string(compressed_string):
    # Декодируем данные из Base64
    compressed_data = base64.b64decode(compressed_string.encode('utf-8'))
    # Распаковываем данные с помощью zlib
    decompressed_data = zlib.decompress(compressed_data)
    return decompressed_data.decode('utf-8')
