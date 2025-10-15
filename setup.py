import setuptools

setuptools.setup(
    name="eol_forum_notifications",
    version="1.0.1",
    author="Oficina EOL UChile",
    author_email="eol-ing@uchile.cl",
    description="Allows you to save forum notification and send mails with threads and/or comments unread among other things",
    url="https://eol.uchile.cl",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "lms.djangoapp": ["eol_forum_notifications = eol_forum_notifications.apps:EolForumNotificationsConfig"]},
)
