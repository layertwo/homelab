import subprocess
import sys

from kirocrew_shim.environment import Settings
from kirocrew_shim.proxy import ModelRejected, Proxy
from kirocrew_shim.translate import plan_argv


def main() -> int:
    settings = Settings()
    plan = plan_argv(sys.argv[1:])

    if plan.exit_code is not None:
        if plan.message:
            print(plan.message)
        return plan.exit_code

    # bufsize=1 (line buffered) with text=True: ACP is newline-delimited, so a
    # block-buffered pipe would stall the handshake waiting to fill 8KiB.
    child = subprocess.Popen(
        [settings.opencode_bin, "acp", *plan.agent_args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        bufsize=1,
        env=settings.child_env,
    )

    proxy = Proxy(
        model=settings.model,
        client_in=sys.stdin,
        client_out=sys.stdout,
        agent_in=child.stdin,
        agent_out=child.stdout,
        log=lambda message: print(message, file=sys.stderr),
    )

    try:
        proxy.run()
    except ModelRejected:
        child.kill()
        return 1

    return child.wait()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
