# https://stackoverflow.com/questions/6931342/system-wide-mutex-in-python-on-linux
import os

if os.name == "nt":
	import msvcrt

	def portable_lock(fp):
		fp.seek(0)
		msvcrt.locking(fp.fileno(), msvcrt.LK_LOCK, 1)

	def portable_unlock(fp):
		fp.seek(0)
		msvcrt.locking(fp.fileno(), msvcrt.LK_UNLCK, 1)
else:
	import fcntl

	def portable_lock(fp):
		fcntl.flock(fp.fileno(), fcntl.LOCK_EX)

	def portable_unlock(fp):
		fcntl.flock(fp.fileno(), fcntl.LOCK_UN)


class Locker:
	def __enter__(self):
		LOCK_FILE_PATH = "./lockfile.lck"
		
		if not os.path.exists(LOCK_FILE_PATH):
			open(LOCK_FILE_PATH, 'a').close()
			
		self.fp = open(LOCK_FILE_PATH)
		portable_lock(self.fp)

	def __exit__(self, _type, value, tb):
		portable_unlock(self.fp)
		self.fp.close()