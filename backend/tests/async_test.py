import asyncio

async def task(name, seconds):
    print(f"task {name} started")
    await asyncio.sleep(seconds)
    print(f"task {name} finished after {seconds} seconds")

async def main():
    await asyncio.gather(
        task("A", 3),
        task("B", 2),
        task("C", 1),
    )

asyncio.run(main())