from setuptools import setup, find_packages

setup(
    name='telegram_notifier_client',
    version='0.9',
    author="Ali Ghorbani",
    author_email='alighorbani29@gmail.com',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    keywords='telegram notifier client',
    url='https://github.com/deusfinance/notifier-client.git',
    install_requires=[
        'requests',
    ],

)
