import json
import os
import pytest
import shlex
import sys
import tempfile

import envkernel

sys.argv[0] = 'envkernel'

def install(d, argv, name='testkernel'):
    """Run envkernel setup, return dict with properties"""
    if isinstance(argv, str):
        argv = shlex.split(argv)
    argv.insert(0, 'envkernel')
    argv[2:2] = ['--name', name, '--prefix', d]
    envkernel.main(argv)
    return get(d, name)

def get(d, name):
    dir_ = os.path.join(d, 'share/jupyter/kernels/', name)
    kernel = json.load(open(os.path.join(dir_, 'kernel.json')))
    return {
        'dir': dir_,
        'kernel': kernel,
        'ek': envkernel.split_doubledash(kernel['argv'])[0],
        'k': envkernel.split_doubledash(kernel['argv'])[1],
        }

@pytest.fixture(scope='function')
def d():
    """Temporary directory for test"""
    with tempfile.TemporaryDirectory() as dir_:
        yield dir_

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
    kern = install(d, "conda /PATH/BBB")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == ['conda', 'run']
    assert kern['ek'][-1] == '/PATH/BBB'

def test_virtualenv(d):
    kern = install(d, "virtualenv /PATH/CCC")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == ['virtualenv', 'run']
    assert kern['ek'][-1] == '/PATH/CCC'

def test_docker(d):
    kern = install(d, "docker IMAGE1")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == ['docker', 'run']
    assert kern['ek'][-1] == 'IMAGE1'

def test_singularity(d):
    kern = install(d, "singularity /PATH/TO/IMAGE2")
    #assert kern['argv'][0] == 'envkernel'  # defined above
    assert kern['ek'][1:3] == ['singularity', 'run']
    assert kern['ek'][-1] == '/PATH/TO/IMAGE2'

