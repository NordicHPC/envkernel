#!/usr/bin/env python3

import argparse
import glob
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

LOG = logging.getLogger('envkernel')
LOG.setLevel(logging.DEBUG)
logging.lastResort.setLevel(logging.DEBUG)



def split_doubledash(argv):
    """Split on '--', for spearating arguments"""
    new = [ ]
    last = 0
    for i, x in enumerate(argv):
        if x == '--':
            new.append(argv[last:i])
            last = i + 1
    new.append(argv[last:])
    return new



def find_connection_file(args):
    for i, a in enumerate(args):
        if a == '-f':
            return args[i+1]



def path_join(*args):
    """Join the arguments using ':', like the PATH environment variable"""
    if len(args) == 1:
        return args[0]
    if args[1] is None or args[1] == '':
        return path_join(args[0], *args[2:])
    path = os.pathsep.join([args[0], args[1]])
    return path_join(path, *args[2:])


def printargs(args):
    return ' '.join(shlex.quote(x) for x in args)



class envkernel():
    def __init__(self, argv):
        LOG.debug('envkernel: cli args: %s', argv)
        self.argv = argv
    def setup(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--name', required=True,
                                  help="Kernel name to install as")
        parser.add_argument('--display-name',
                                  help="Display name of kernel")
        parser.add_argument('--user', action='store_true', default=False,
                            help="Install kernel to user dir")
        parser.add_argument('--sys-prefix', action='store_true',
                            help="Install kernel to this Python's sys.prefix")
        parser.add_argument('--prefix',
                            help="Install kernel to this prefix")
        parser.add_argument('--replace', action='store_true',
                            help="Replace existing kernel")
        parser.add_argument('--kernel', default='ipykernel',
                            help="Kernel to install, options are ipykernel or ir (default ipykernel).  This "
                                 "simply sets the --kernel-cmd and --language options to the proper "
                                 "values for these well-known kernels.  It could break, however. --kernel-cmd "
                                 "overrides this.")
        parser.add_argument('--python', default='python',
                            help="Python command to run (default 'python')")
        parser.add_argument('--kernel-cmd',
                            help="Kernel command to run, separated by spaces.  If this is given, --python is not used.")
        parser.add_argument('--language',
                            help="Language to put into kernel file (default based on --kernel)")
        args, unknown_args = parser.parse_known_args(sys.argv[2:])
        LOG.debug('setup: args: %s', args)
        LOG.debug('setup: unknown_args: %s', unknown_args)
        self.setup_args = args
        self.name = args.name
        self.display_name = args.display_name
        self.user = args.user
        if args.sys_prefix:
            self.prefix = sys.prefix
        else:
            self.prefix = args.prefix
        self.replace = args.replace
        self.python = args.python
        if self.python == "SELF":
            self.python = sys.executable
        # Setting/detecting language and kernel command
        if args.kernel_cmd:
            self.language = 'python'
            self.kernel_cmd = args.kernel_cmd.split()
        elif args.kernel == 'ipykernel':
            self.language = 'python'
            self.kernel_cmd = [args.python,
                               "-m",
                               "ipykernel_launcher",
                               "-f",
                               "{connection_file}",
                               ]
        elif args.kernel == 'ir':
            self.language = 'R'
            self.kernel_cmd = ['R',
                               '--slave',
                               '-e',
                               'IRkernel::main()',
                               '--args',
                               '{connection_file}']
        elif args.kernel == 'imatlab':
            self.language = 'matlab'
            self.kernel_cmd = [args.python,
                               '-m',
                               'imatlab',
                               '-f',
                               '{connection_file}']
        else:
            LOG.critical("Unknown kernel: %s", args.kernel)
        if args.language:
            self.language = args.language
        # Copy logos from upstream packages, if exists
        self.logos = None
        if self.language == 'python':
            try:
                import ipykernel
                ipykernel_dir = os.path.dirname(ipykernel.__file__)
                logos = glob.glob(os.path.join(ipykernel_dir, 'resources', '*'))
                self.logos = logos
            except ImportError:
                LOG.debug("Could not automatically find ipykernel logos")
        #
        self.argv = unknown_args

    def _get_parser(self):
        pass

    def install_kernel(self, kernel, name, user=False, replace=None, prefix=None, logos=None):
        """Install a kernel (as given by json) to a kernel directory

        A thin wrapper around jupyter_client.kernelspec.KernelSpecManager().install_kernel_spec.

        kernel: kernel JSON
        name: kernel name
        """
        import jupyter_client.kernelspec
        #jupyter_client.kernelspec.KernelSpecManager().get_kernel_spec('python3').argv

        with tempfile.TemporaryDirectory(prefix='jupyter-kernel-secure-') \
          as kernel_dir:
            open(os.path.join(kernel_dir, 'kernel.json'), 'w').write(
                json.dumps(kernel, sort_keys=True, indent=4))
            if self.logos:
                if isinstance(self.logos, str) and os.path.isdir(self.logos):
                    self.logos = os.path.listdir(self.logos)
                for logo in self.logos:
                    shutil.copy(logo, kernel_dir)
            jupyter_client.kernelspec.KernelSpecManager().install_kernel_spec(
                kernel_dir, kernel_name=name,
                user=user, replace=replace, prefix=prefix)

        LOG.info("")
        LOG.info("  Kernel saved to {}".format(jupyter_client.kernelspec.KernelSpecManager().get_kernel_spec(name).resource_dir))
        LOG.info("  Command line: %s", kernel['argv'])



class lmod(envkernel):
    def setup(self):
        super().setup()
        argv = [
            os.path.realpath(sys.argv[0]),
            self.__class__.__name__, 'run',
            *self.argv,
            '--',
            #self.setup_args.python,
            #"-m",
            #"ipykernel_launcher",
            #"-f",
            #"{connection_file}",
            *self.kernel_cmd,
        ]
        kernel = {
            "argv": argv,
            "display_name": (self.display_name if self.display_name
                      else "Lmod kernel with {}".format(' '.join(self.argv))),
            "language": self.language,
            }
        self.install_kernel(kernel, name=self.name, user=self.user,
                            replace=self.replace, prefix=self.prefix)

    def run(self):
        """load modules and run:

        before '--': the modules to load
        after '--': the Python command to run after loading"""
        argv, rest = split_doubledash(self.argv)
        parser = argparse.ArgumentParser()
        parser.add_argument('--purge', action='store_true', default=False, help="Purge existing modules first")
        parser.add_argument('module', nargs='+')
        args, unknown_args = parser.parse_known_args(argv)

        #print(args)
        #print('stderr', args, file=sys.stderr)
        LOG.debug('run: args: %s', args)
        LOG.debug('run: unknown_args: %s', unknown_args)

        #LMOD_INIT = os.environ['LMOD_PKG']+'/init/env_modules_python.py'
        #exec(compile(open(LMOD_INIT).read(), LMOD_INIT, 'exec'))
        def module(command, *arguments):
            """Copy of the lmod command above, but works on python2&3

            ... to work around old lmod installations that don't have
            python3 support.
            """
            commands = os.popen(
                '%s/libexec/lmod python %s %s'\
                % (os.environ['LMOD_PKG'], command, ' '.join(arguments))).read()
            exec(commands)
        if args.purge:
            LOG.debug('Lmod purging')
            module('purge')
        LOG.debug('Lmod loading ' + ' '.join(args.module))
        module('load', *args.module)

        os.execvp(rest[0], rest)



class conda(envkernel):
    def setup(self):
        super().setup()
        parser = argparse.ArgumentParser()
        parser.add_argument('path')
        args, unknown_args = parser.parse_known_args(self.argv)

        argv = [
            os.path.realpath(sys.argv[0]),
            self.__class__.__name__, 'run',
            *unknown_args,
            args.path,
            '--',
            *self.kernel_cmd,
        ]
        default_display_name = "{} ({}, {})".format(
            os.path.basename(args.path.strip('/')),
            self.__class__.__name__,
            args.path)
        kernel = {
            "argv": argv,
            "display_name": (self.display_name if self.display_name
                      else default_display_name),
            "language": self.language,
            }
        self.install_kernel(kernel, name=self.name, user=self.user,
                            replace=self.replace, prefix=self.prefix)

    def run(self):
        """load modules and run:

        before '--': the modules to load
        after '--': the Python command to run after loading"""
        argv, rest = split_doubledash(self.argv)
        parser = argparse.ArgumentParser()
        #parser.add_argument('--purge', action='store_true', default=False, help="Purge existing modules first")
        parser.add_argument('path')
        args, unknown_args = parser.parse_known_args(argv)

        #print(args)
        #print('stderr', args, file=sys.stderr)
        LOG.debug('run: args: %s', args)
        LOG.debug('run: unknown_args: %s', unknown_args)

        path = args.path
        if not os.path.exists(path):
            LOG.critical("%s path does not exist: %s", self.__class__.__name__, path)
            raise RuntimeError("envkernel: {} path {} does not exist".format(self.__class__.__name__, path))
        if not os.path.exists(os.path.join(path, 'bin')):
            LOG.critical("%s bin does not exist: %s/bin", self.__class__.__name__, path)
            raise RuntimeError("envkernel: {} path {} does not exist".format(self.__class__.__name__, path+'/bin'))

        self._run(args, rest)

    def _run(self, args, rest):
        path = args.path
        os.environ['PATH']            = path_join(os.path.join(path, 'bin'    ), os.environ.get('PATH', None))
        os.environ['CPATH']           = path_join(os.path.join(path, 'include'), os.environ.get('CPATH', None))
        os.environ['LD_LIBRARY_PATH'] = path_join(os.path.join(path, 'lib'    ), os.environ.get('LD_LIBRARY_PATH', None))
        os.environ['LIBRARY_PATH']    = path_join(os.path.join(path, 'bin'    ), os.environ.get('LIBRARY_PATH', None))

        os.execvp(rest[0], rest)



class virtualenv(conda):
    def _run(self, args, rest):
        path = args.path
        os.environ.pop('PYTHONHOME')
        os.environ['PATH'] = path_join(os.path.join(path, 'bin'), os.environ.get('PATH', None))
        if 'PS1' in os.environ:
            os.environ['PS1'] = "(venv3) " + os.environ['PS1']

        os.execvp(rest[0], rest)



class docker(envkernel):
    def setup(self):
        super().setup()
        parser = argparse.ArgumentParser()
        parser.add_argument('image')
        args, unknown_args = parser.parse_known_args(self.argv)
        LOG.debug('setup: %s', args)

        argv = [
            os.path.realpath(sys.argv[0]),
            'docker',
            'run',
            '--connection-file', '{connection_file}',
            args.image,
            #*[ '--mount={}'.format(x) for x in args.mount],
            *unknown_args,
            '--',
            #self.setup_args.python,
            #"-m",
            #"ipykernel_launcher",
            #"-f",
            #"{connection_file}",
            *self.kernel_cmd,
        ]

        kernel = {
            "argv": argv,
            "display_name": (self.display_name if self.display_name
                      else "Docker with {}".format(args.image)),
            "language": self.language,
            }
        self.install_kernel(kernel, name=self.name, user=self.user,
                            replace=self.replace, prefix=self.prefix)

    def run(self):
        argv, rest = split_doubledash(self.argv)
        parser = argparse.ArgumentParser()
        parser.add_argument('image', help='Dcker image name')
        #parser.add_argument('--mount', '-m', action='append', default=[],
        #                        help='mount to set up, format hostDir:containerMountPoint')
        parser.add_argument('--copy-workdir', default=False, action='store_true')
        parser.add_argument('--workdir')
        parser.add_argument('--pwd', action='store_true')
        parser.add_argument('--connection-file', help="Do not use, internal use.")

        args, unknown_args = parser.parse_known_args(argv)

        extra_mounts = [ ]
        extra_ports = [ ]

        # working dir
        if args.pwd or args.workdir:
            workdir = os.getcwd()
            if args.workdir:
                workdir = args.workdir
            # src = host data, dst=container mountpoint
            expose_mounts.extend(["--mount", "type=bind,source={},destination={},ro={}{}".format(os.getcwd(), workdir, 'false', ',copy' if args.copy_workdir else '')])

        cmd = [
            "docker", "run", "--rm", "-i",
            "--user", "%d:%d"%(os.getuid(), os.getgid()),
            ]

        # Parse connection file
        connection_file = args.connection_file
        connection_data = json.load(open(connection_file))
        # Find all the (five) necessary ports
        for var in ('shell_port', 'iopub_port', 'stdin_port', 'control_port', 'hb_port'):
            # Forward each port to itself
            port = connection_data[var]
            #expose_ports.append((connection_data[var], connection_data[var]))
            cmd.extend(['--expose={}'.format(port), "-p", "{}:{}".format(port, port)])
        # Mount the connection file inside the container
        extra_mounts.extend(["--mount",
                             "type=bind,source={},destination={},ro={}".format(
                                 connection_file, connection_file, 'false'
                                                                              )
                            ])
        #expose_mounts.append(dict(src=json_file, dst=json_file))

        # Change connection_file to bind to all IPs.
        connection_data['ip'] = '0.0.0.0'
        open(connection_file, 'w').write(json.dumps(connection_data))

        # Add options to expose the ports
#       for port_host, port_container in expose_ports:
#           cmd.extend(['--expose={}'.format(port_container), "-p", "{}:{}".format(port_host, port_container)])

        ## Add options for exposing mounts
        #tmpdirs = [ ]  # keep reference to clean up later
        #for mount in expose_mounts:
        #    src = mount['src']  # host data
        #    dst = mount['dst']  # container mountpoint
        #    if mount.get('copy'):
        #        tmpdir = tempfile.TemporaryDirectory(prefix='jupyter-secure-')
        #        tmpdirs.append(tmpdir)
        #        src = tmpdir.name + '/copy'
        #        shutil.copytree(mount['src'], src)
        #    cmd.extend(["--mount", "type=bind,source={},destination={},ro={}".format(src, dst, 'true' if mount.get('ro') else 'false')])  # ro=true
        #cmd.extend(("--workdir", workdir))

        # Process all of our mounts, to do two things:
        #  Substitute {workdir} with
        unknown_args.extend(extra_mounts)
        tmpdirs = []
        for i, arg in enumerate(unknown_args):
            if '{workdir}' in arg and copy_workdir:
                arg = arg + ',copy'
            arg.format(workdir=os.getcwd)
            if ',copy' in arg:
                src_original = re.search('src=([^,]+)', arg).group(1)
                # Copy the source directory
                tmpdir = tempfile.TemporaryDirectory(prefix='jupyter-secure-')
                tmpdirs.append(tmpdir)
                src = tmpdir.name + '/copy'
                shutil.copytree(src_original, src)
                #
                newarg = re.sub('src=([^,]+)', 'src='+src, arg) # add in new src
                newarg = re.sub(',copy', '', newarg)            # remove ,copy
                unknown_args[i] = newarg

        # Image name
#       cmd.append(args.image)

        # Remainder of all other arguments from the kernel specification
        cmd.extend([
            *unknown_args,
#           '--debug',
            args.image,
            *rest,
            ])

        # Run...
        LOG.info('docker: running cmd = %s', printargs(cmd))
        ret = subprocess.call(cmd)

        # Clean up all temparary directories
        for tmpdir in tmpdirs:
            tmpdir.cleanup()
        exit(ret)


class singularity(envkernel):
    def setup(self):
        """Install a new singularity kernelspec"""
        super().setup()
        parser = argparse.ArgumentParser()
        parser.add_argument('image')
        args, unknown_args = parser.parse_known_args(self.argv)
        LOG.debug('setup: args: %s', args)
        LOG.debug('setup: unknown_args: %s', unknown_args)

        argv = [
            os.path.realpath(sys.argv[0]),
            'singularity', 'run',
            '--connection-file', '{connection_file}',
            #*[ '--mount={}'.format(x) for x in args.mount],
            *unknown_args,
            args.image,
            '--',
            #self.setup_args.python,
            #"-m",
            #"ipykernel_launcher",
            #"-f",
            #"/connection.json",
            #"{connection_file}",
            *self.kernel_cmd,
        ]

        kernel = {
            "argv": argv,
            "display_name": (self.display_name if self.display_name
                      else "Singularity with {}".format(args.image)),
            "language": self.language,
            }
        self.install_kernel(kernel, name=self.name, user=self.user,
                            replace=self.replace, prefix=self.prefix)

    def run(self):
        argv, rest = split_doubledash(self.argv)
        parser = argparse.ArgumentParser()
        parser.add_argument('image', help='image name')
        parser.add_argument('--mount', '-m', action='append', default=[],
                            help='mount to set up, format hostDir:containerMountPoint')
        #parser.add_argument('--copy-pwd', default=False, action='store_true')
        parser.add_argument('--pwd', action='store_true')
        parser.add_argument('--connection-file')
        args, unknown_args = parser.parse_known_args(argv)
        LOG.debug('run: args: %s', args)
        LOG.debug('run: unknown_args: %s', unknown_args)
        LOG.debug('run: rest: %s', rest)

        extra_args = [ ]

        # Find connection file and mount it:
        connection_file = args.connection_file
        # If we mount with --contain, then /tmp is missing and *can't*
        # have any extra files mounted inside of it.  This means that
        # we have to relocate the connection file to "/" or somewhere.
        new_connection_file = "/"+os.path.basename(connection_file)
        if False:
            # Re-copy connection file to /tmp
            # Doesn't work now!
            f = tempfile.NamedTemporaryFile(
                    suffix='-'+os.path.basename(connection_file))
            f.write(open(connection_file, 'rb').read())
            f.close()
            i = rest.index(connection_file)
            rest[i] = f.name
        else:
            # enable overlay = yes
            # We can directly mount the connection file in...
            extra_args.extend(['--bind', connection_file+":"+new_connection_file])

        if args.pwd:
            extra_args.extend(['--bind', os.getcwd()])
            extra_args.extend(['--pwd', os.getcwd()])

        # Replace the connection file path with the new location.
        idx = rest.index(connection_file)
        rest[idx] = new_connection_file

        # In Singularity 2.4 at least, --pwd does not work when used
        # with --contain.  This manually does it using a bash cd + exec.
        if ('-c' in unknown_args or '--contain' in unknown_args ) and args.pwd:
            rest = ["bash", "-c", "cd %s"%os.getcwd() + " ; exec "+(" ".join(shlex.quote(x) for x in rest))]

        cmd = [
            'singularity',
            'exec',
            *extra_args,
            *unknown_args,
            args.image,
            *rest,
            ]

        LOG.debug('singularity: running cmd= %s', printargs(cmd))
        subprocess.call(cmd)

def main():
    mod = sys.argv[1]
    cls = globals()[mod]
    if len(sys.argv) > 2 and sys.argv[2] == 'run':
        cls(sys.argv[3:]).run()
    else:
        cls(sys.argv[2:]).setup()

if __name__ == '__main__':
    main()
