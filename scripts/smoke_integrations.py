"""Exercise the frozen agent entry points without starting the audio daemon."""
import asyncio
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main(engine: str) -> None:
    launcher = Path(__file__).resolve().parents[1] / 'hooks' / 'native.sh'
    environment = {**os.environ, 'NOISY_STUDIO_ENGINE': str(Path(engine).resolve())}
    parameters = StdioServerParameters(command='sh', args=[str(launcher), 'mcp'], env=environment)
    with tempfile.TemporaryFile(mode='w+') as errors:
        async with asyncio.timeout(45):
            async with stdio_client(parameters, errlog=errors) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    names = {tool.name for tool in result.tools}
                    if not {'speak', 'announce'} <= names:
                        raise RuntimeError('Frozen MCP is missing speech tools')
        errors.seek(0)
        if 'Traceback' in errors.read():
            raise RuntimeError('Frozen MCP reported an exception during startup or shutdown')
    hook = subprocess.run(
        ['sh', str(launcher), 'hook'], input='{}', text=True,
        capture_output=True, env=environment, timeout=15,
    )
    if (hook.returncode, hook.stdout, hook.stderr) != (0, '', ''):
        raise RuntimeError('Frozen hook did not exit silently for an empty event')
    print('Frozen MCP handshake, speech tool discovery and hook entry point passed.')


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1]))
