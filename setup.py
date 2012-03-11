from setuptools import setup

from push_to_talk_app import get_version

setup(
    name='push_to_talk',
    version=get_version(),
    url='http://bitbucket.org/latestrevision/linux-push-to-talk/',
    description='Push-to-talk functionality for Linux',
    author='Adam Coddington',
    author_email='me@adamcoddington.net',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
    ],
    packages=['push_to_talk_app', 'push_to_talk_app.interfaces', ],
    entry_points={
            'console_scripts': [
                'ptt = push_to_talk_app.application:run_from_cmdline',
                ],
        },
    install_requires = [
            #'pygtk',
            'python-xlib',
        ],
    include_package_data=True
)
