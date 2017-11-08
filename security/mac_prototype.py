import hmac
import hashlib
import base64

def gen(key, packet):	
	hash = hmac.new(key, packet, hashlib.sha256)
	# to lowercase hexits
	hash.hexdigest()
	# to base64
	return base64.b64encode(hash.digest())

def main():
	h = hashlib.sha256()
	h.update(b"111")
	h.hexdigest()
	k = h.digest()
	message = bytes('<our packet as a string>', 'utf-8')
	print(gen(k, message))

if __name__ == '__main__':
	main()