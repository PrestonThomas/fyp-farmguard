from setuptools import setup, find_packages

setup(
    name='your_project_name',
    version='0.1',
    packages=find_packages(),
    entry_points={
        'amqtt.broker.plugins': [
            'topic_checker_plugin = topic_checker_plugin:TopicEventPlugin',
        ],
    },
)
