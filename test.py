import time
import asyncio

# 定義非同步函式
async def hello():
  asyncio.sleep(1)
  print('Hello World:%s' % time.time())

def run():
  for i in range(5):
    loop.run_until_complete(hello())

loop = asyncio.get_event_loop()
if __name__ =='__main__':
  run()
