import json
import logging
import os
from os.path import join as pjoin
import pytest
import shlex
import subprocess
import sys
import tempfile

import envkernel

sys.argv[0] = 'envkernel'

TEST_CONNECTION_FILE = """\
{
  "shell_port": 10000,
  "iopub_port": 10001,
  "stdin_port": 10002,
  "control_port": 10003,
  "hb_port": 10004,
  "ip": "127.0.0.1",
  "key": "00000000-000000000000000000000000",
  "transport": "tcp",
  "signature_scheme": "hmac-sha256",
  "kernel_name": ""
}
"""
ALL_MODULES = ["conda", "virtualenv", "lmod", "docker", "singularity"]


def install(d, argv, name='testkernel'):
    """Run envkernel setup, return dict with properties"""
    if isinstance(argv, str):
        argv = shlex.split(argv)
    argv.insert(0, 'envkernel')
    argv[2:2] = ['--name', name, '--prefix', d]
    envkernel.main(argv)
    return get(d, name)

def get(d, name):
    """From an installed kernel, return dict with properties for testing."""
    dir_ = pjoin(d, 'share/jupyter/kernels/', name)
    kernel = json.load(open(pjoin(dir_, 'kernel.json')))
    return {
        'dir': dir_,
        'kernel': kernel,
        'ek': envkernel.split_doubledash(kernel['argv'])[0],
        'k': envkernel.split_doubledash(kernel['argv'])[1],
        }

def run(d, kern, execvp=lambda _argv0, argv: 0):
    """Start envkernel in "run" mode to see if it can run successfully.
    """
    connection_file = pjoin(d, 'connection.json')
    open(connection_file, 'w').write(TEST_CONNECTION_FILE)
    # Do basic tests
    argv = kern['kernel']['argv']
    clsname = argv[1]
    assert argv[2] == 'run'
    # Replace connecton file
    argv = [ replace_conn_file(x, connection_file) for x in argv ]
    # Setup object, override the execvp for the function, run.
    ek = getattr(envkernel, clsname)(argv[3:])
    ek.execvp = execvp
    ek.run()

@pytest.fixture(scope='function')
def d():
    """Temporary directory for test"""
    with tempfile.TemporaryDirectory() as dir_:
        yield dir_

def replace_conn_file(arg, connection_file):
    if isinstance(arg, list):
        return [ replace_conn_file(x, connection_file) for x in arg ]
    if arg == '{connection_file}':
        return connection_file
    else:
        return arg

def all_modes(modes=None):
    if not modes:
        modes = ALL_MODULES
    return pytest.mark.parametrize("mode", modes)

def is_sublist(list_, sublist):
    """A sublist is part of a given list"""
    return any(list_[i:i+len(sublist)] == sublist
               for i in range(len(list_)-len(sublist)+1))




@all_modes()
def test_basic(d, mode):
    kern = install(d, "%s TESTTARGET"%mode)
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == [mode, 'run']

@all_modes()
def test_display_name(d, mode):
    kern = install(d, "%s --display-name=AAA TESTTARGET"%mode)
    assert kern['kernel']['display_name'] == 'AAA'

@all_modes(['conda'])
def test_template(d, mode):
    os.environ['JUPYTER_PATH'] = pjoin(d, 'share/jupyter')
    subprocess.call("python -m ipykernel install --name=aaa-ipy --display-name=BBB --prefix=%s"%d, shell=True)
    #os.environ['ENVKERNEL_TESTPATH'] = os.path.join(d, 'share/jupyter/kernels')
    kern = install(d, "%s --kernel-template aaa-ipy TESTTARGET"%mode)
    assert kern['kernel']['display_name'] == 'BBB'

@all_modes(['conda'])
def test_template_copyfiles(d, mode):
    os.environ['JUPYTER_PATH'] = pjoin(d, 'share/jupyter')
    subprocess.call("python -m ipykernel install --name=aaa-ipy --display-name=BBB --prefix=%s"%d, shell=True)
    f = open(pjoin(d, 'share/jupyter/kernels/', 'aaa-ipy', 'A.txt'), 'w')
    f.write('LMNO')
    f.close()
    kern = install(d, "%s --kernel-template aaa-ipy TESTTARGET"%mode)
    assert os.path.exists(pjoin(kern['dir'], 'A.txt'))
    assert open(pjoin(kern['dir'], 'A.txt')).read() == 'LMNO'

@all_modes(['conda'])
def test_template_make_path_relative(d, mode):
    os.environ['JUPYTER_PATH'] = pjoin(d, 'share/jupyter')
    subprocess.call("python -m ipykernel install --name=aaa-ipy --display-name=BBB --prefix=%s"%d, shell=True)
    # First test it without, ensure it has the full path
    kern = install(d, "%s --kernel-template aaa-ipy TESTTARGET"%mode)
    assert kern['k'][0] != 'python' # This is an absolete path
    # Now test it with --kernel-make-path-relative and ensure it's relative
    kern = install(d, "%s --kernel-template aaa-ipy --kernel-make-path-relative TESTTARGET"%mode)
    assert kern['k'][0] == 'python' # This is an absolete path

def test_help():
    """Test that the global -h option works and prints module names"""
    p = subprocess.Popen("python -m envkernel -h", shell=True, stdout=subprocess.PIPE)
    stdout = p.stdout.read().decode()
    p.wait()
    for mod in ALL_MODULES:
        assert mod in stdout, "%s not found in --help output"%mod
    assert p.returncode == 0

def test_logging(d, caplog):
    """Test that the global -v option works and increases debugging

    Run first without -v and make sure some stuff isn't printed.
    Then, run with -v and ensure that the argument processing is output.
    """
    cmd = "python3 -m envkernel lmod --name=ABC --display-name=AAA LMOD --prefix=%s"%d
    print(d)
    env = os.environ.copy()
    env['JUPYTER_PATH'] = pjoin(d, 'share/jupyter')
    # First, test non-verbose (should have minimal output)
    p = subprocess.Popen(cmd, env=env,
                         shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout = p.stdout.read().decode()
    p.wait()
    print(stdout)
    assert 'Namespace' not in stdout
    assert 'kernel-specific' not in stdout
    assert 'Kernel command:' in stdout
    # Now test verbose (should have some debugging info)
    p = subprocess.Popen(cmd+' -v', env=env,
                         shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout = p.stdout.read().decode()
    p.wait()
    #print(stdout)
    assert 'Namespace' in stdout
    assert 'kernel-specific' in stdout
    assert 'Kernel command:' in stdout

def test_umask(d):
    orig_umask = os.umask(0)
    # Test multiple umasks, and kerneldir + kernel.json
    for umask in [0, 0o022]:
        os.umask(umask)
        kern = install(d, "lmod TESTTARGET")
        assert os.stat(kern['dir']).st_mode & 0o777  ==  0o777&(~umask)
        assert os.stat(pjoin(kern['dir'], 'kernel.json')).st_mode & 0o777  ==  0o666&(~umask)
    os.umask(orig_umask)


@all_modes()
def test_set_python(d, mode):
    kern = install(d, "%s --python=AAA TESTTARGET"%mode)
    assert kern['k'][0] == 'AAA'

@all_modes()
def test_set_kernel_cmd(d, mode):
    kern = install(d, "%s --kernel-cmd='a b c d' TESTTARGET"%mode)
    assert kern['k'] == ['a', 'b', 'c', 'd']

@all_modes()
def test_language(d, mode):
    kern = install(d, "%s --language=AAA TESTTARGET"%mode)
    assert kern['kernel']['language'] == 'AAA'

@all_modes()
def test_env(d, mode):
    kern = install(d, "%s --env=AAA=BBB --env=CCC=DDD TESTTARGET"%mode)
    assert kern['kernel']['env']['AAA'] == 'BBB'
    assert kern['kernel']['env']['CCC'] == 'DDD'


def test_recursive_run(d):
    """Test envkernel being called on itself.

    Roughly runs this, which :

    envkernel lmod --name=test1 LMOD
    envkernel conda --kernel-template=test1 --name=test1 CPATH
    """
    # Must set JUPYTER_PATH to be able to load the new kernel template
    os.environ['JUPYTER_PATH'] = pjoin(d, 'share/jupyter')
    kern1 = install(d, "lmod LMOD", name='test1')
    #print(kern1['kernel']['argv'])
    # Test the conda install
    CPATH = pjoin(d, 'test-conda')
    os.mkdir(CPATH)
    os.mkdir(pjoin(CPATH, 'bin'))
    kern2 = install(d, "conda --kernel-template=test1 %s"%CPATH, name='test1')
    #print(kern2['kernel']['argv'])
    def test_exec(_file, _args):
        #print(kern1['kernel']['argv'])
        # Exclude the last argument, which is the connection file
        assert _args[:-1] == kern1['kernel']['argv'][:-1]
    run(d, kern2, test_exec)



# Languages
@all_modes()
def test_default_language(d, mode):
    # default language is ipykernel
    kern = install(d, "%s TESTTARGET"%mode)
    assert kern['kernel']['language'] == 'python'
    assert kern['k'][0] == 'python'
    assert kern['k'][1:4] == ['-m', 'ipykernel_launcher', '-f']

@all_modes()
def test_ipykernel(d, mode):
    kern = install(d, "%s --kernel=ipykernel TESTTARGET"%mode)
    assert kern['kernel']['language'] == 'python'
    assert kern['k'][0] == 'python'
    assert kern['k'][1:4] == ['-m', 'ipykernel_launcher', '-f']

@all_modes()
def test_ir(d, mode):
    kern = install(d, "%s --kernel=ir TESTTARGET"%mode)
    assert kern['kernel']['language'] == 'R'
    assert kern['k'][0] == 'R'
    assert kern['k'][1:5] == ['--slave', '-e', 'IRkernel::main()', '--args']

@all_modes()
def test_imatlab(d, mode):
    kern = install(d, "%s --kernel=imatlab TESTTARGET"%mode)
    assert kern['kernel']['language'] == 'matlab'
    assert kern['k'][0].endswith('python')
    assert kern['k'][1:4] == ['-m', 'imatlab', '-f']



# Test setting up specific kernels
def test_lmod(d):
    kern = install(d, "lmod MOD1 MOD2")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == ['lmod', 'run']
    assert kern['ek'][-2] == 'MOD1'
    assert kern['ek'][-1] == 'MOD2'

def test_lmod_purge(d):
    kern = install(d, "lmod --purge MOD3")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert '--purge' in kern['ek'][3:]
    assert kern['ek'][-1] == 'MOD3'

def test_conda(d):
    kern = install(d, "conda test-data/env")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == ['conda', 'run']
    assert kern['ek'][-1].endswith('test-data/env')

def test_virtualenv(d):
    kern = install(d, "virtualenv test-data/env")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == ['virtualenv', 'run']
    assert kern['ek'][-1].endswith('test-data/env')

def test_docker(d):
    kern = install(d, "docker --some-arg=AAA TESTIMAGE")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == ['docker', 'run']
    assert kern['ek'][-2] == 'TESTIMAGE'
    assert '--some-arg=AAA' in kern['ek']

def test_singularity(d):
    kern = install(d, "singularity --some-arg=AAA /PATH/TO/TESTIMAGE2")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == ['singularity', 'run']
    assert kern['ek'][-2] == '/PATH/TO/TESTIMAGE2'
    assert '--some-arg=AAA' in kern['ek']



# Test running kernels
def test_run_conda(d):
    PATH = pjoin(d, 'test-conda')
    os.mkdir(PATH)
    os.mkdir(pjoin(PATH, 'bin'))

    def test_exec(_file, _args):
        assert pjoin(PATH, 'bin') in os.environ['PATH'].split(':')
        assert pjoin(PATH, 'include') in os.environ['CPATH'].split(':')
        assert pjoin(PATH, 'lib') in os.environ['LD_LIBRARY_PATH'].split(':')
        assert pjoin(PATH, 'lib') in os.environ['LIBRARY_PATH'].split(':')
    kern = install(d, "conda %s"%PATH)
    run(d, kern, test_exec)

def test_run_venv(d):
    PATH = pjoin(d, 'test-venv')
    os.mkdir(PATH)
    os.mkdir(pjoin(PATH, 'bin'))

    def test_exec(_file, _args):
        assert pjoin(PATH, 'bin') in os.environ['PATH'].split(':')
    kern = install(d, "virtualenv %s"%PATH)
    run(d, kern, test_exec)

# Requires lmod installed... and a module to exist
#def test_run_lmod(d):

def test_run_docker(d):
    def test_exec(_file, argv):
        assert argv[0:5] == ['docker', 'run', '--rm', '-i', '--user']
        for port in range(10000, 10005):
            assert '--expose=%d'%port in argv
            assert is_sublist(argv, ['-p', '%d:%d'%(port, port)])
        assert '--some-arg=AAA' in argv
        assert 'IMAGE' in argv
        i = argv.index('-f')
        assert json.loads(open(argv[i+1]).read())['ip'] == '0.0.0.0'
        connection_file = pjoin(d, 'connection.json')
        assert is_sublist(argv, ["--mount", "type=bind,source=%s,destination=%s,ro=false"%(connection_file, connection_file)])
    kern = install(d, "docker --some-arg=AAA IMAGE")
    run(d, kern, test_exec)

    # Test the --pwd option, and also that it does not go when it is NOT present
    pwd_mount = ["--mount", "type=bind,source=%s,destination=%s,ro=false"%(os.getcwd(), os.getcwd())]
    def test_exec(_file, argv):
        assert is_sublist(argv, pwd_mount)
    kern = install(d, "docker --some-arg=AAA --pwd IMAGE")
    run(d, kern, test_exec)
    # Test above, but reversed
    def test_exec(_file, argv):
        assert not is_sublist(argv, pwd_mount)
    kern = install(d, "docker --some-arg=AAA IMAGE")
    run(d, kern, test_exec)
    # Custom workdir
    pwd_mount = ["--mount", "type=bind,source=%s,destination=%s,ro=false"%(os.getcwd(), '/WORKDIR')]
    def test_exec(_file, argv):
        assert is_sublist(argv, pwd_mount)
    kern = install(d, "docker --some-arg=AAA --workdir=/WORKDIR IMAGE")
    run(d, kern, test_exec)


def test_run_singularity(d):
    def test_exec(_file, argv):
        assert argv[0] == 'singularity'
        assert '--some-arg=AAA' in argv
        assert os.path.join(os.getcwd(), 'IMAGE') in argv
    kern = install(d, "singularity --some-arg=AAA IMAGE")
    run(d, kern, test_exec)

    def test_exec(_file, argv):
        assert argv[0] == 'singularity'
        assert is_sublist(argv, ['--bind', os.getcwd()])
        assert is_sublist(argv, ['--pwd', os.getcwd()])
        #assert is_sublist(argv, ['--bind', '/PATH/AAA:/PATH/AAA'])
    kern = install(d, "singularity --pwd IMAGE")
    run(d, kern, test_exec)
