import hmac
import hashlib
import base64
import time
import datetime
import pyblake2


'''
Convert arbitrary PIN to a 256-bit key
'''
def pin_to_key(pin):
	h = hashlib.sha256()
	h.update(pin)
	h.hexdigest()
	return h.digest()

'''
	SHA256 HMAC
'''
def sha256_hmac(key, packet):	
	hash = hmac.new(key, packet, hashlib.sha256)
	# to lowercase hexits
	hash.hexdigest()
	# to base64
	return base64.b64encode(hash.digest())

def sha256_verify(key, packet, sig):
	good_sig = sha256_hmac(key, packet)
	return hmac.compare_digest(good_sig, sig)


'''
	blake2s HMAC library example
'''
DIG_SIZE2 = 4 # in bytes
KEY2 = b""
S_KEY = b"34c0eb22f5f08c4ad26c05a84aefd70c95fce0691ee0f967e14cf4f6a63d8ccb"
S_PIN = b"12345"

def blake2s_hmac(packet):
	# h = hmac.new(KEY2, digestmod=hashlib.blake2s)	
	h = pyblake2.blake2s( digest_size=DIG_SIZE2, key=KEY2 )
	h.update(packet)
	# print("Digest Size: " + str(h.digest_size) )
	return h.digest()

def blake2s_verify(packet, sig):
	good_sig = blake2s_hmac(packet)
	# use compare_digest() for timing based attacks
	return hmac.compare_digest(good_sig, sig)


def set_key():
	today = datetime.datetime.now()
	r = today.day + today.month + today.year
	temp = bytes(r)
	global KEY2 
	KEY2 = pin_to_key(S_PIN + temp + S_KEY  )

def main():
	set_key()
	print(S_PIN)

	packet = b"098928472someinforandsomecommand<<end"
	invalid_packet = b"098928472someinforandsomecommand<<<end"
	invalid_sig = b"e3c8102868d28b5ff85fc35dda07329970d1a01e273c37481326fe0c861c8142"

	# Begin calls
	sig = blake2s_hmac(packet)
	print("digest:")
	print(sig)

	print( KEY2 )
	
	print( blake2s_verify(packet, sig) )
	print( blake2s_verify(packet, invalid_sig) )
	print( blake2s_verify(invalid_packet, sig) )
	print( blake2s_verify(invalid_packet, invalid_sig) )
	


if __name__ == '__main__':
	main()

# print( hashlib.algorithms_guaranteed) 