# wccgo_v2
## Personal blog   http://wccgo.herokuapp.com
The website is powered by Flask framework, with relational database Postgresql, and deployed on the Heroku platform. 
The website has realized functions such as user registration, blog publication, classification with label, commentary and personal information management. 
The website has also been integrated with a rich text editor Ckeditor, which supports code highlighting.
As a technology blog, I will regularly share some learning experience on this site.

## V2(2017/01/03)
* 添加留言板板块，用来发表短博客
* 给删除按钮加了确认框,避免误删长博客
* 修复代码高亮的显示bug
* 发现Heroku平台不支持图片、视频的永久存储，因而删除了这部分代码
* TODO: 为Ckeditor整合mathjax数学公式插件
