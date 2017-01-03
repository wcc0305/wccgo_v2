# -*- coding: utf-8 -*-
from flask_wtf import Form
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField, Field
from wtforms.validators import DataRequired, Length, Email, Regexp, ValidationError
from..models import User, Role, Tag
from flaskckeditor import CKEditor
from wtforms.widgets import TextInput


class NameForm(Form):
    name = StringField('What is your name?', validators=[DataRequired()])
    submit = SubmitField('Submit')


class EditProfileForm(Form):
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')


class EditProfileAdminForm(Form):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    username = StringField('Username', validators=[
        DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
        'Usernames must have only letters, '
        'numbers, dots or underscores')])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int)
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name) for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


class CommentForm(Form):
    body = StringField('', validators=[DataRequired()])
    submit = SubmitField('Submit')


class ShortCommentForm(Form):
    body = StringField('', validators=[DataRequired()])
    submit = SubmitField('Submit')

class TagListField(Field):
    widget = TextInput()

    def __init__(self, label=None, validators=None,
                 **kwargs):
        super(TagListField, self).__init__(label, validators, **kwargs)

    def _value(self):
        if self.data:
            r = ''
            for obj in self.data:
                r += self.obj_to_str(obj)
                r += ';'    #以;为间隔
            return r[:-1]    #参考代码里有问题，已修改，而且要r[:-1]，否则修改的时候，后面多一个分号，再提交的时候就多了空格这个tag
        else:
            return ''

    def process_formdata(self, valuelist):
        print 'process_formdata..'
        print valuelist
        if valuelist:
            tags = self._remove_duplicates([x.strip() for x in valuelist[0].split(';')])   #以;为间隔
            self.data = [self.str_to_obj(tag) for tag in tags]
        else:
            self.data = None

    def pre_validate(self, form):
        pass

    @classmethod
    def _remove_duplicates(cls, seq):
        """去重"""
        d = {}
        for item in seq:
            if item.lower() not in d:
                d[item.lower()] = True
                yield item

    @classmethod
    def str_to_obj(cls, tag):
        """将字符串转换位obj对象"""
        tag_obj = Tag.query.filter_by(name=tag).first()
        if tag_obj is None:
            tag_obj = Tag(name=tag)
        return tag_obj

    @classmethod
    def obj_to_str(cls, obj):
        """将对象转换为字符串"""
        if obj:
            return obj.name
        else:
            return ''


class PostForm(Form, CKEditor): #是否需要继承自CKEditor??要的 两个父类写的次序有区分
    body = TextAreaField("What's on your mind?", validators=[DataRequired()])
    title = StringField("the title:", validators=[DataRequired()])
    tags = TagListField("标签", validators=[DataRequired()])
    submit = SubmitField('Submit')


class ShortPostForm(Form, CKEditor):
    body = TextAreaField("What's on your mind?", validators=[DataRequired()])
    submit = SubmitField('Submit')