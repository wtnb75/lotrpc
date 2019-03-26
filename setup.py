from setuptools import setup
from lotrpc.version import VERSION

with open("README.md") as f:
    long_descr = f.read()

setup(
    name="lotrpc",
    version=VERSION,
    description="RPC abstraction layer",
    long_description=long_descr,
    long_description_content_type="text/markdown",
    author="Takashi WATANABE",
    author_email="wtnb75@gmail.com",
    url="https://github.com/wtnb75/lotrpc",
    packages=["lotrpc", "lotrpc.grpc", "lotrpc.json", "lotrpc.mp",
              "lotrpc.msgpack", "lotrpc.sunrpc", "lotrpc.xdr", "lotrpc.xml", "lotrpc.zero"],
    license="MIT",
    install_requires=open("requirements.txt").readlines(),
    extras_require={
        "development": open("requirements-dev.txt").readlines(),
    },
    entry_points={
        "console_scripts": [
            "lotrpc-example = lotrpc.clsrv:cli"
            "lotrpc-rpcgen = lotrpc.rpcgen:cli"
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Communications',
        'Programming Language :: Python :: 3',
    ],
    python_requires='>=3',
    keywords="rpc proxy grpc zerorpc json xml messagepack",
)
