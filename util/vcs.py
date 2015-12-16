import subprocess


def git_command(args, cwd):
    """Wrapper to run a Git command."""
    # Using shell, just pass a string to subprocess.
    p = subprocess.Popen(" ".join(['git'] + args),
                         stdout=subprocess.PIPE,
                         shell=True,
                         cwd=cwd)
    out, err = p.communicate()
    return out.decode('utf-8')
