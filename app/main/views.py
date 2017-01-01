# -*- coding: utf-8 -*-
from datetime import datetime
from flask import render_template, session, redirect, url_for, abort, flash, request, current_app, make_response
from. import main
from.forms import NameForm, EditProfileForm, EditProfileAdminForm, PostForm, CommentForm, ShortPostForm, ShortCommentForm
from.. import db
from..models import User, Role, Permission, Post, Comment, Tag, Short_Post, Short_Comment
from flask.ext.login import current_user, login_required
from ..decorators import admin_required, permission_required
import os, random


@main.route('/', methods=['GET', 'POST'])
def index():
    form = PostForm()
    if current_user.can(Permission.WRITE_ARTICLES) and form.validate_on_submit():
        post = Post(body=form.body.data, author=current_user._get_current_object())
        post.title = form.title.data
        post.tags = form.tags.data
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    tags = Tag.query.all()
    return render_template('index.html', form=form, posts=posts, Permission=Permission,
                           pagination=pagination, tags=tags)#Permission=Permission加上才行


@main.route('/new_post', methods=['GET', 'POST'])
def new_post():
    form = PostForm()
    if current_user.can(Permission.WRITE_ARTICLES) and form.validate_on_submit():
        post = Post(body=form.body.data, author=current_user._get_current_object())
        post.title = form.title.data
        post.tags = form.tags.data
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('.index'))
    return render_template('new_post.html', form=form, Permission=Permission)


@main.route('/tag/<int:id>', methods=['GET', 'POST'])   #methods对吗？
def tag(id):
    tag = Tag.query.filter_by(id=id).first()
    page = request.args.get('page', 1, type=int)
    pagination = tag.posts.paginate(       #查询所有包含该tag的posts,model里要有lazy='dynamic'，这里还需要在仔细看看
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('tag.html', tagname=tag.name, id=id, posts=posts, Permission=Permission, pagination=pagination)


@main.route('/delete_post/<int:id>')
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id)
    if current_user == post.author:
        db.session.delete(post)
        db.session.commit()
        flash('A post has been successfully deleted!')
    return redirect(url_for('.index'))


@main.route('/delete_comment/<int:id>')
@login_required
def delete_comment(id):
    comment = Comment.query.get_or_404(id)
    if current_user == comment.author or current_user.is_administrator():
        db.session.delete(comment)
        db.session.commit()
        flash('A comment has been successfully deleted!')
        post = Post.query.filter_by(id=comment.post_id).first()
    return redirect(url_for('.post', id=post.id))
    #删除评论后，redirect到当前post


@main.route('/delete_short_post/<int:id>')
@login_required
def delete_short_post(id):
    short_post = Short_Post.query.get_or_404(id)
    if current_user == short_post.author:
        db.session.delete(short_post)
        db.session.commit()
        flash('A post has been successfully deleted!')
    return redirect(url_for('.short_post_index'))


@main.route('/delete_short_comment/<int:id>')
@login_required
def delete_short_comment(id):
    short_comment = Short_Comment.query.get_or_404(id)
    if current_user == short_comment.author or current_user.is_administrator():
        db.session.delete(short_comment)
        db.session.commit()
        flash('A comment has been successfully deleted!')
        short_post = Short_Post.query.filter_by(id=short_comment.short_post_id).first()
    return redirect(url_for('.short_post', id=short_post.id))


@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    return render_template('user.html', user=user, Permission=Permission)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        db.session.commit()
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form, Permission=Permission)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):#其实是添加用户，不能修改已有用户的信息
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user, Permission=Permission)


@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, post=post, author=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been published.')
        return redirect(url_for('.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) / current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'], error_out=False)
    comments = pagination.items
    return render_template('post.html', posts=[post], form=form, comments=comments, pagination=pagination, Permission=Permission)


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        post.title = form.title.data
        post.tags = form.tags.data
        db.session.add(post)
        db.session.commit()
        flash('The post has been updated.')
        return redirect(url_for('main.post', id=post.id))
    form.body.data = post.body
    form.title.data = post.title
    form.tags.data = post.tags #多对多查询
    return render_template('edit_post.html', form=form, Permission=Permission)


def gen_rnd_filename():
    filename_prefix = datetime.now().strftime('%Y%m%d%H%M%S')
    return '%s%s' % (filename_prefix, str(random.randrange(1000, 10000)))


@main.route('/ckupload/', methods=['POST'])
def ckupload():
    """CKEditor file upload"""
    error = ''
    url = ''
    callback = request.args.get("CKEditorFuncNum")
    if request.method == 'POST' and 'upload' in request.files:
        fileobj = request.files['upload']
        fname, fext = os.path.splitext(fileobj.filename)
        rnd_name = '%s%s' % (gen_rnd_filename(), fext)
        filepath = os.path.join(current_app.static_folder, 'upload', rnd_name)
        # 检查路径是否存在，不存在则创建
        dirname = os.path.dirname(filepath)
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except:
                error = 'ERROR_CREATE_DIR'
        elif not os.access(dirname, os.W_OK):
            error = 'ERROR_DIR_NOT_WRITEABLE'
        if not error:
            fileobj.save(filepath)
            url = url_for('static', filename='%s/%s' % ('upload', rnd_name))
    else:
        error = 'post error'
    res = """

<script type="text/javascript">
  window.parent.CKEDITOR.tools.callFunction(%s, '%s', '%s');
</script>

""" % (callback, url, error)
    #print "url=" + url
    #print "error=" + error
    response = current_app.make_response(res)
    response.headers["Content-Type"] = "text/html"
    return response


@main.route('/short_post_index',methods=['GET','POST'])
def short_post_index():
    form = ShortPostForm()
    if current_user.can(Permission.WRITE_ARTICLES) and form.validate_on_submit():
        shortpost = Short_Post(body=form.body.data, author=current_user._get_current_object())
        db.session.add(shortpost)
        db.session.commit()
        return redirect(url_for('main.short_post_index'))
    page = request.args.get('page', 1, type=int)
    pagination = Short_Post.query.order_by(Short_Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    short_posts = pagination.items
    return render_template('short_post_index.html', short_posts=short_posts, form=form,
                           pagination=pagination, Permission=Permission)


@main.route('/short_post/<int:id>', methods=['GET', 'POST'])
def short_post(id):
    short_post = Short_Post.query.get_or_404(id)
    form = ShortCommentForm()
    if form.validate_on_submit():
        short_comment = Short_Comment(body=form.body.data, short_post=short_post, author=current_user._get_current_object())
        db.session.add(short_comment)
        db.session.commit()
        flash('Your comment has been published.')
        return redirect(url_for('.short_post', id=short_post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (short_post.short_comments.count() - 1) / current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
    pagination = short_post.short_comments.order_by(Short_Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'], error_out=False)
    short_comments = pagination.items
    return render_template('short_post.html', short_posts=[short_post], form=form, comments=short_comments, pagination=pagination, Permission=Permission)

