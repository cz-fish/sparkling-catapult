This project is a small picture-based blog webpage hosted on github (pages). Each blog post will be a picture, with a title, date, potentially a short text. Most posts will belong to series (called stories). The blog will allow browsing posts in chronological order, but also individual stories. Browsing should be allowed both newest first, as well as newest last. The blog should also allow searching by words in titles and the short text. The browsing should be paginated. The webpage should support for styling via css stylesheets, although in the initial version there will only be one style.

To create and update the content, this is the workflow:
- add a picture to a pictures directory
- add a small yaml file, one yaml per blog post - with the data and metadata - title, picture, date, series (plus ordinal number in the series), short text
- run a Python script that takes all the yamls and (re-)builds a full static webpage on the gh-pages git branch that can just be uploaded to github
