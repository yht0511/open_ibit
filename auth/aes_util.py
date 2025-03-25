import secrets
from base64 import b64encode
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

AES_CHARS = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"

def random_string(length: int) -> str:
    return ''.join(secrets.choice(AES_CHARS) for _ in range(length))

def encrypt_aes(data: str, key: str, iv: str) -> str:
    key_bytes = key.encode('utf-8')
    iv_bytes = iv.encode('utf-8')
    data_bytes = data.encode('utf-8')
    
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
    ct_bytes = cipher.encrypt(pad(data_bytes, AES.block_size))
    return b64encode(ct_bytes).decode('utf-8')

def encrypt_password(password: str, salt: str) -> str:
    if not salt:
        return password
    random_prefix = random_string(64)
    iv = random_string(16)
    data = random_prefix + password
    return encrypt_aes(data, salt, iv)
