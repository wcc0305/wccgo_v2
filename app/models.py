# -*- coding: utf-8 -*-
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask.ext.login import UserMixin, AnonymousUserMixin
from flask import current_app
from . import login_manager
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from datetime import datetime, timedelta
import hashlib
from flask import request
from markdown import markdown
import bleach





class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.COMMENT |
                     Permission.WRITE_SHORT_POSTS, True),
            'PARTNER': (Permission.COMMENT |
                        Permission.WRITE_POSTS |
                        Permission.WRITE_SHORT_POSTS, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name


class Permission:
    #FOLLOW = 0x01  #这项权限空缺，将来可以再补
    COMMENT = 0x02
    WRITE_POSTS = 0x04
    WRITE_SHORT_POSTS = 0x08
    ADMINISTER = 0x80


class User(UserMixin,db.Model):  #也要继承UserMixin，这个类实现了许多登录验证等有用的方法
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    short_posts = db.relationship('Short_Post', backref='author', lazy='dynamic')#相当于short_post里也有了author这一列
    avatar_hash = db.Column(db.String(32))
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    short_comments = db.relationship('Short_Comment', backref='author', lazy='dynamic')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            print self.email
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
        if self.role is None:
            self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)# password_hash也成了User类里的一个属性

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User %r>' % self.username

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        db.session.commit()
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def can(self, permissions):
        return self.role is not None and (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        db.session.commit()
        return True

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
            hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(url=url, hash=hash, size=size, default=default,
                                                                     rating=rating)


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False
#AnonymousUser的实例可以用can()方法,AnonymousUserMixin的不可以

login_manager.anonymous_user = AnonymousUser #有了这一句，current_user在没有登录的时候，才会被当做是AnonymousUser


# 是否要放到User类里面
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))


# 文章和标签的映射表 ，多对多关系
post_tag_ref = db.Table('post_tag_ref',
                        db.Column('post_id', db.Integer, db.ForeignKey('posts.id')),
                        db.Column('tag_id',  db.Integer, db.ForeignKey('tags.id')))


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    #这里的backref='post'是在Comment的实体里，引用post的名字
    tags = db.relationship('Tag', secondary='post_tag_ref', backref=db.backref('posts', lazy='dynamic'))
        #lazy='dynamic'必须要有，否则按tags查询post会有问题
        #若删除一篇post，也会删除post_tag_ref里的记录，但当tag已不再对应任何一篇post，也不会删除

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'strong', 'ul','pre',
                        'h1', 'h2', 'h3', 'p', 'img','br','hr',
                        'table','tbody','tr','td','s'
        ] #若是有哪个元素显示不出来，就要在allowed_tags里加
        attrs = {
            '*': ['class', 'style'],
            'a': ['href', 'rel'],
            'img': ['alt', 'src'],
            'table':['cellpadding','cellspacing','style','border','align'],
        }
        styles=['color','width','height']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, attributes=attrs, styles=styles, strip=True))

db.event.listen(Post.body, 'set', Post.on_changed_body)


class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True)


class Short_Post(db.Model):
    __tablename__ = 'short_posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    short_comments = db.relationship('Short_Comment', backref='short_post', lazy='dynamic')


class Short_Comment(db.Model):
    __tablename__ = 'short_comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    short_post_id = db.Column(db.Integer, db.ForeignKey('short_posts.id'))
