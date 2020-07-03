#!/usr/bin/env python

import os
import subprocess
import web

class reload_service_linkchecker:
    def GET(self, path):

        if path == "/" + str(os.getenv('WS_GIT_RELOAD_TOKEN')):
            cmd = None
            try:
                cmd = subprocess.Popen(['/usr/local/bin/git-pull-conf.sh'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = cmd.communicate()
                return "OK" + "\n\nSTDOUT\n" + stdout.decode() + "\nSTDERR\n" + stderr.decode()
            except subprocess.TimeoutExpired as msg:
                cmd.kill()
                return "KO" + "\n\n" + str(msg)
            except Exception as msg:
                return "KO" + "\n\n" + str(msg)

        return "KO"

def main():
    urls = (
            '(.*)', 'reload_service_linkchecker'
            )

    app = web.application(urls, globals())
    app.run()

if __name__ == "__main__":
    main()
