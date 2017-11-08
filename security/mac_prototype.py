import hmac
import hashlib
import base64
from hashlib import blake2b
from hmac import compare_digest

def gen(key, packet):	
	hash = hmac.new(key, packet, hashlib.sha256)
	# to lowercase hexits
	hash.hexdigest()
	# to base64
	return base64.b64encode(hash.digest())

SECRET_KEY = b'pseudorandomly generated server secret key'
AUTH_SIZE = 16

def sign(packet):
    h = blake2b(digest_size=AUTH_SIZE, key=SECRET_KEY)
    h.update(packet)
    return h.hexdigest().encode('utf-8')

def verify(packet, sig):
    good_sig = sign(packet)
    return compare_digest(good_sig, sig)




def main():
	h = hashlib.sha256()
	h.update(b"111")
	h.hexdigest()
	k = h.digest()
	message = bytes('<our packet as a string>', 'utf-8')
	print(gen(k, message))

	packet = b'<from-device-a>'
	sig = sign(packet)
	print("{0},{1}".format(packet.decode('utf-8'), sig))
	print('Verified: ' + str (verify(packet, sig)) )

if __name__ == '__main__':
	main()