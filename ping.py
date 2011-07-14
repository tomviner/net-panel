import re
import subprocess
import time


class Ping(object):
    def test_connection():
        p = subprocess.Popen(
            ('ping', '-c 1', '-n', '8.8.8.8'),
            stdout=subprocess.PIPE)
        stdout = p.communicate()[0]
        if not p.returncode:
            ptime = re.findall(r' (time=[\d.]+ ms)', stdout)
            if ptime:
                return ptime[0]
        return False

tester = Ping()
while True:
    res = tester.test_connection()
    print res
    if res:
        print 'Net Found', 
        break
    time.sleep(1)
