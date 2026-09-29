#!/usr/bin/env python3
"""sprint4.py - social: posts, likes, comments, follows."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


T: dict[str, str] = {}

# ============================================================== ALEMBIC
T["backend/alembic/versions/0005_sprint4.py"] = _t('''
    """sprint 4: posts, likes, comments, follows

    Revision ID: 0005
    Revises: 0004
    Create Date: 2025-05-01
    """
    from __future__ import annotations

    from typing import Sequence, Union

    from alembic import op
    import sqlalchemy as sa

    revision: str = "0005"
    down_revision: Union[str, None] = "0004"
    branch_labels: Union[str, Sequence[str], None] = None
    depends_on: Union[str, Sequence[str], None] = None


    def upgrade() -> None:
        op.create_table(
            "posts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "author_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("text", sa.Text(), nullable=True),
            sa.Column(
                "attachment_id",
                sa.Integer(),
                sa.ForeignKey("files.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index("ix_posts_author_id", "posts", ["author_id"])
        op.create_index("ix_posts_created_at", "posts", ["created_at"])

        op.create_table(
            "post_likes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "post_id",
                sa.Integer(),
                sa.ForeignKey("posts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint("post_id", "user_id", name="uq_post_like"),
        )

        op.create_table(
            "post_comments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "post_id",
                sa.Integer(),
                sa.ForeignKey("posts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "author_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index("ix_post_comments_post_id", "post_comments", ["post_id"])

        op.create_table(
            "follows",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "follower_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "following_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint("follower_id", "following_id", name="uq_follow"),
        )
        op.create_index("ix_follows_follower", "follows", ["follower_id"])
        op.create_index("ix_follows_following", "follows", ["following_id"])


    def downgrade() -> None:
        op.drop_table("follows")
        op.drop_table("post_comments")
        op.drop_table("post_likes")
        op.drop_table("posts")
''')

# ============================================================== MODELS
T["backend/app/models.py"] = _t('''
    from __future__ import annotations

    from datetime import datetime
    from sqlalchemy import (
        Boolean,
        DateTime,
        ForeignKey,
        Integer,
        String,
        Text,
        UniqueConstraint,
        func,
    )
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


    class Base(DeclarativeBase):
        pass


    class User(Base):
        __tablename__ = "users"

        id: Mapped[int] = mapped_column(primary_key=True)
        username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
        email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
        hashed_password: Mapped[str] = mapped_column(String(255))
        display_name: Mapped[str | None] = mapped_column(String(100), default=None)
        bio: Mapped[str | None] = mapped_column(String(500), default=None)
        avatar_color: Mapped[str | None] = mapped_column(String(20), default=None)
        is_active: Mapped[bool] = mapped_column(Boolean, default=True)
        last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )


    class File(Base):
        __tablename__ = "files"

        id: Mapped[int] = mapped_column(primary_key=True)
        owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
        filename: Mapped[str] = mapped_column(String(255))
        content_type: Mapped[str] = mapped_column(String(100))
        size: Mapped[int] = mapped_column(Integer)
        storage_name: Mapped[str] = mapped_column(String(120), unique=True)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )


    class Chat(Base):
        __tablename__ = "chats"

        id: Mapped[int] = mapped_column(primary_key=True)
        title: Mapped[str | None] = mapped_column(String(255), default=None)
        description: Mapped[str | None] = mapped_column(String(500), default=None)
        avatar_color: Mapped[str | None] = mapped_column(String(20), default=None)
        invite_token: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
        is_group: Mapped[bool] = mapped_column(Boolean, default=False)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )


    class ChatMember(Base):
        __tablename__ = "chat_members"
        __table_args__ = (UniqueConstraint("chat_id", "user_id", name="uq_chat_user"),)

        id: Mapped[int] = mapped_column(primary_key=True)
        chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
        user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
        role: Mapped[str] = mapped_column(String(20), default="member")
        last_read_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )


    class Message(Base):
        __tablename__ = "messages"

        id: Mapped[int] = mapped_column(primary_key=True)
        chat_id: Mapped[int] = mapped_column(
            ForeignKey("chats.id", ondelete="CASCADE"), index=True
        )
        author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
        text: Mapped[str | None] = mapped_column(Text, nullable=True)
        message_type: Mapped[str] = mapped_column(String(20), default="text")
        attachment_id: Mapped[int | None] = mapped_column(
            ForeignKey("files.id", ondelete="SET NULL"), nullable=True
        )
        reply_to_id: Mapped[int | None] = mapped_column(
            ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
        )
        edited_at: Mapped[datetime | None] = mapped_column(
            DateTime(timezone=True), nullable=True
        )
        is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
        )


    class Post(Base):
        __tablename__ = "posts"

        id: Mapped[int] = mapped_column(primary_key=True)
        author_id: Mapped[int] = mapped_column(
            ForeignKey("users.id", ondelete="CASCADE"), index=True
        )
        text: Mapped[str | None] = mapped_column(Text, nullable=True)
        attachment_id: Mapped[int | None] = mapped_column(
            ForeignKey("files.id", ondelete="SET NULL"), nullable=True
        )
        is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
        )


    class PostLike(Base):
        __tablename__ = "post_likes"
        __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_post_like"),)

        id: Mapped[int] = mapped_column(primary_key=True)
        post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"))
        user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )


    class PostComment(Base):
        __tablename__ = "post_comments"

        id: Mapped[int] = mapped_column(primary_key=True)
        post_id: Mapped[int] = mapped_column(
            ForeignKey("posts.id", ondelete="CASCADE"), index=True
        )
        author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
        text: Mapped[str] = mapped_column(Text)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )


    class Follow(Base):
        __tablename__ = "follows"
        __table_args__ = (UniqueConstraint("follower_id", "following_id", name="uq_follow"),)

        id: Mapped[int] = mapped_column(primary_key=True)
        follower_id: Mapped[int] = mapped_column(
            ForeignKey("users.id", ondelete="CASCADE"), index=True
        )
        following_id: Mapped[int] = mapped_column(
            ForeignKey("users.id", ondelete="CASCADE"), index=True
        )
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )
''')

# ============================================================== SCHEMAS
T["backend/app/schemas.py"] = _t('''
    from __future__ import annotations

    from datetime import datetime
    from pydantic import BaseModel, ConfigDict, EmailStr, Field


    class RegisterRequest(BaseModel):
        username: str = Field(min_length=3, max_length=50)
        email: EmailStr
        password: str = Field(min_length=8, max_length=128)
        display_name: str | None = None


    class LoginRequest(BaseModel):
        username: str
        password: str


    class TokenResponse(BaseModel):
        access_token: str
        token_type: str = "bearer"


    class UserRead(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        id: int
        username: str
        email: EmailStr
        display_name: str | None
        bio: str | None = None
        avatar_color: str | None = None
        is_active: bool
        last_seen: datetime | None = None
        created_at: datetime


    class UserProfile(BaseModel):
        id: int
        username: str
        display_name: str | None
        bio: str | None
        avatar_color: str | None
        created_at: datetime
        posts_count: int
        followers_count: int
        following_count: int
        is_following: bool
        is_me: bool


    class UserUpdate(BaseModel):
        display_name: str | None = Field(default=None, max_length=100)
        bio: str | None = Field(default=None, max_length=500)


    class ChatCreate(BaseModel):
        title: str | None = None
        is_group: bool = False
        member_usernames: list[str] = Field(default_factory=list)


    class ChatUpdate(BaseModel):
        title: str | None = Field(default=None, max_length=255)
        description: str | None = Field(default=None, max_length=500)
        avatar_color: str | None = Field(default=None, max_length=20)


    class ChatMemberRead(BaseModel):
        user_id: int
        username: str
        display_name: str | None
        avatar_color: str | None
        role: str
        joined_at: datetime


    class AddMemberRequest(BaseModel):
        username: str


    class InviteRead(BaseModel):
        token: str
        url: str


    class FileRead(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        id: int
        filename: str
        content_type: str
        size: int
        created_at: datetime


    class MessageRead(BaseModel):
        id: int
        chat_id: int
        author_id: int
        author_username: str
        author_display: str | None = None
        author_avatar_color: str | None = None
        text: str | None = None
        message_type: str = "text"
        attachment: FileRead | None = None
        reply_to_id: int | None = None
        reply_preview: str | None = None
        reply_author: str | None = None
        edited_at: datetime | None = None
        is_deleted: bool = False
        created_at: datetime


    class ChatRead(BaseModel):
        id: int
        title: str | None
        description: str | None = None
        avatar_color: str | None = None
        is_group: bool
        created_at: datetime
        last_message: MessageRead | None = None
        unread_count: int = 0
        peer: UserRead | None = None
        member_count: int = 0
        my_role: str | None = None


    class MessageCreate(BaseModel):
        text: str | None = Field(default=None, max_length=4000)
        message_type: str = "text"
        attachment_id: int | None = None
        reply_to_id: int | None = None


    class MessageEdit(BaseModel):
        text: str = Field(min_length=1, max_length=4000)


    class PostCreate(BaseModel):
        text: str | None = Field(default=None, max_length=5000)
        attachment_id: int | None = None


    class PostAuthor(BaseModel):
        id: int
        username: str
        display_name: str | None
        avatar_color: str | None


    class PostCommentRead(BaseModel):
        id: int
        post_id: int
        author: PostAuthor
        text: str
        created_at: datetime


    class PostRead(BaseModel):
        id: int
        author: PostAuthor
        text: str | None
        attachment: FileRead | None
        is_deleted: bool
        created_at: datetime
        likes_count: int
        comments_count: int
        is_liked: bool
        is_mine: bool


    class PostCommentCreate(BaseModel):
        text: str = Field(min_length=1, max_length=2000)
''')

# ============================================================== POSTS ROUTER
T["backend/app/routers/posts.py"] = _t('''
    from __future__ import annotations

    from fastapi import APIRouter, Depends, HTTPException, Query, status
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import File as FileModel, Follow, Post, PostComment, PostLike, User
    from app.schemas import (
        FileRead,
        PostAuthor,
        PostCommentCreate,
        PostCommentRead,
        PostCreate,
        PostRead,
    )


    router = APIRouter()


    async def _post_to_read(db: AsyncSession, p: Post, current_id: int) -> PostRead:
        author = (await db.execute(select(User).where(User.id == p.author_id))).scalar_one()

        attachment = None
        if p.attachment_id:
            f = (await db.execute(
                select(FileModel).where(FileModel.id == p.attachment_id)
            )).scalar_one_or_none()
            if f:
                attachment = FileRead.model_validate(f)

        likes_count = int((await db.execute(
            select(func.count(PostLike.id)).where(PostLike.post_id == p.id)
        )).scalar() or 0)

        comments_count = int((await db.execute(
            select(func.count(PostComment.id)).where(PostComment.post_id == p.id)
        )).scalar() or 0)

        is_liked = (await db.execute(
            select(PostLike).where(
                PostLike.post_id == p.id, PostLike.user_id == current_id
            )
        )).scalar_one_or_none() is not None

        return PostRead(
            id=p.id,
            author=PostAuthor(
                id=author.id,
                username=author.username,
                display_name=author.display_name,
                avatar_color=author.avatar_color,
            ),
            text="Пост удалён" if p.is_deleted else p.text,
            attachment=attachment,
            is_deleted=p.is_deleted,
            created_at=p.created_at,
            likes_count=likes_count,
            comments_count=comments_count,
            is_liked=is_liked,
            is_mine=p.author_id == current_id,
        )


    @router.post("", response_model=PostRead, status_code=status.HTTP_201_CREATED)
    async def create_post(
        payload: PostCreate,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        if not (payload.text and payload.text.strip()) and not payload.attachment_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty post")
        p = Post(
            author_id=current.id,
            text=payload.text,
            attachment_id=payload.attachment_id,
        )
        db.add(p)
        await db.flush()
        await db.refresh(p)
        return await _post_to_read(db, p, current.id)


    @router.get("/feed", response_model=list[PostRead])
    async def feed(
        current: CurrentUser,
        limit: int = Query(50, le=100),
        db: AsyncSession = Depends(get_session),
    ):
        following = select(Follow.following_id).where(Follow.follower_id == current.id)
        stmt = (
            select(Post)
            .where(
                Post.is_deleted == False,  # noqa: E712
                (Post.author_id == current.id) | (Post.author_id.in_(following)),
            )
            .order_by(Post.created_at.desc())
            .limit(limit)
        )
        posts = (await db.execute(stmt)).scalars().all()
        return [await _post_to_read(db, p, current.id) for p in posts]


    @router.get("/user/{user_id}", response_model=list[PostRead])
    async def user_posts(
        user_id: int,
        current: CurrentUser,
        limit: int = Query(50, le=100),
        db: AsyncSession = Depends(get_session),
    ):
        stmt = (
            select(Post)
            .where(Post.author_id == user_id, Post.is_deleted == False)  # noqa: E712
            .order_by(Post.created_at.desc())
            .limit(limit)
        )
        posts = (await db.execute(stmt)).scalars().all()
        return [await _post_to_read(db, p, current.id) for p in posts]


    @router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_post(
        post_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        p = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
        if p is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "post not found")
        if p.author_id != current.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not your post")
        p.is_deleted = True
        p.text = ""
        await db.flush()


    @router.post("/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
    async def like_post(
        post_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        p = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
        if p is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "post not found")
        existing = (await db.execute(
            select(PostLike).where(
                PostLike.post_id == post_id, PostLike.user_id == current.id
            )
        )).scalar_one_or_none()
        if existing is None:
            db.add(PostLike(post_id=post_id, user_id=current.id))
            await db.flush()


    @router.delete("/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
    async def unlike_post(
        post_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        like = (await db.execute(
            select(PostLike).where(
                PostLike.post_id == post_id, PostLike.user_id == current.id
            )
        )).scalar_one_or_none()
        if like:
            await db.delete(like)
            await db.flush()


    @router.get("/{post_id}/comments", response_model=list[PostCommentRead])
    async def list_comments(
        post_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        stmt = (
            select(PostComment, User)
            .join(User, User.id == PostComment.author_id)
            .where(PostComment.post_id == post_id)
            .order_by(PostComment.created_at.asc())
        )
        rows = (await db.execute(stmt)).all()
        return [
            PostCommentRead(
                id=c.id,
                post_id=c.post_id,
                author=PostAuthor(
                    id=u.id,
                    username=u.username,
                    display_name=u.display_name,
                    avatar_color=u.avatar_color,
                ),
                text=c.text,
                created_at=c.created_at,
            )
            for c, u in rows
        ]


    @router.post(
        "/{post_id}/comments",
        response_model=PostCommentRead,
        status_code=status.HTTP_201_CREATED,
    )
    async def add_comment(
        post_id: int,
        payload: PostCommentCreate,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        p = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
        if p is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "post not found")

        c = PostComment(post_id=post_id, author_id=current.id, text=payload.text)
        db.add(c)
        await db.flush()
        await db.refresh(c)

        return PostCommentRead(
            id=c.id,
            post_id=c.post_id,
            author=PostAuthor(
                id=current.id,
                username=current.username,
                display_name=current.display_name,
                avatar_color=current.avatar_color,
            ),
            text=c.text,
            created_at=c.created_at,
        )


    @router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_comment(
        comment_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        c = (await db.execute(
            select(PostComment).where(PostComment.id == comment_id)
        )).scalar_one_or_none()
        if c is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "comment not found")
        if c.author_id != current.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not your comment")
        await db.delete(c)
        await db.flush()
''')

# ============================================================== USERS ROUTER (follow + profile)
T["backend/app/routers/users.py"] = _t('''
    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import func, or_, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import Follow, Post, User
    from app.schemas import UserProfile, UserRead, UserUpdate


    router = APIRouter()


    @router.get("", response_model=list[UserRead])
    async def list_users(
        current: CurrentUser,
        q: str | None = None,
        limit: int = 50,
        db: AsyncSession = Depends(get_session),
    ):
        stmt = select(User).where(User.id != current.id)
        if q:
            p = f"%{q}%"
            stmt = stmt.where(or_(User.username.ilike(p), User.display_name.ilike(p)))
        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return [UserRead.model_validate(u) for u in result.scalars().all()]


    @router.patch("/me", response_model=UserRead)
    async def update_me(
        payload: UserUpdate, current: CurrentUser, db: AsyncSession = Depends(get_session)
    ):
        if payload.display_name is not None:
            current.display_name = payload.display_name or None
        if payload.bio is not None:
            current.bio = payload.bio or None
        await db.flush()
        await db.refresh(current)
        return UserRead.model_validate(current)


    @router.get("/{user_id}/profile", response_model=UserProfile)
    async def user_profile(
        user_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if u is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")

        posts_count = int((await db.execute(
            select(func.count(Post.id)).where(
                Post.author_id == user_id, Post.is_deleted == False  # noqa: E712
            )
        )).scalar() or 0)

        followers_count = int((await db.execute(
            select(func.count(Follow.id)).where(Follow.following_id == user_id)
        )).scalar() or 0)

        following_count = int((await db.execute(
            select(func.count(Follow.id)).where(Follow.follower_id == user_id)
        )).scalar() or 0)

        is_following = (await db.execute(
            select(Follow).where(
                Follow.follower_id == current.id, Follow.following_id == user_id
            )
        )).scalar_one_or_none() is not None

        return UserProfile(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            bio=u.bio,
            avatar_color=u.avatar_color,
            created_at=u.created_at,
            posts_count=posts_count,
            followers_count=followers_count,
            following_count=following_count,
            is_following=is_following,
            is_me=u.id == current.id,
        )


    @router.post("/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
    async def follow_user(
        user_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        if user_id == current.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot follow self")
        u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if u is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
        existing = (await db.execute(
            select(Follow).where(
                Follow.follower_id == current.id, Follow.following_id == user_id
            )
        )).scalar_one_or_none()
        if existing is None:
            db.add(Follow(follower_id=current.id, following_id=user_id))
            await db.flush()


    @router.delete("/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
    async def unfollow_user(
        user_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        f = (await db.execute(
            select(Follow).where(
                Follow.follower_id == current.id, Follow.following_id == user_id
            )
        )).scalar_one_or_none()
        if f:
            await db.delete(f)
            await db.flush()
''')

# ============================================================== MAIN
T["backend/app/main.py"] = _t('''
    from contextlib import asynccontextmanager

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.config import settings
    from app.db import engine
    from app.routers import auth, chats, files, messages, posts, users, ws
    from app.websocket_manager import manager


    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.upload_path
        yield
        await manager.close_all()
        await engine.dispose()


    app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    p = settings.API_V1_PREFIX
    app.include_router(auth.router, prefix=f"{p}/auth", tags=["auth"])
    app.include_router(users.router, prefix=f"{p}/users", tags=["users"])
    app.include_router(chats.router, prefix=f"{p}/chats", tags=["chats"])
    app.include_router(messages.router, prefix=f"{p}/chats", tags=["messages"])
    app.include_router(files.router, prefix=f"{p}/files", tags=["files"])
    app.include_router(posts.router, prefix=f"{p}/posts", tags=["posts"])
    app.include_router(ws.router, prefix=p, tags=["ws"])


    @app.get("/health")
    async def health():
        return {"status": "ok", "app": settings.APP_NAME}
''')

# ============================================================== FRONTEND
T["frontend/src/types.ts"] = _t('''
    export interface User {
      id: number;
      username: string;
      email: string;
      display_name: string | null;
      bio: string | null;
      avatar_color: string | null;
      is_active: boolean;
      last_seen: string | null;
      created_at: string;
    }

    export interface UserProfile {
      id: number;
      username: string;
      display_name: string | null;
      bio: string | null;
      avatar_color: string | null;
      created_at: string;
      posts_count: number;
      followers_count: number;
      following_count: number;
      is_following: boolean;
      is_me: boolean;
    }

    export interface Chat {
      id: number;
      title: string | null;
      description: string | null;
      avatar_color: string | null;
      is_group: boolean;
      created_at: string;
      last_message: Message | null;
      unread_count: number;
      peer: User | null;
      member_count: number;
      my_role: string | null;
    }

    export interface ChatMember {
      user_id: number;
      username: string;
      display_name: string | null;
      avatar_color: string | null;
      role: "owner" | "admin" | "member";
      joined_at: string;
    }

    export interface Attachment {
      id: number;
      filename: string;
      content_type: string;
      size: number;
      created_at: string;
    }

    export type MessageType = "text" | "image" | "file" | "voice" | "sticker" | "system";

    export interface Message {
      id: number;
      chat_id: number;
      author_id: number;
      author_username: string;
      author_display: string | null;
      author_avatar_color: string | null;
      text: string | null;
      message_type: MessageType;
      attachment: Attachment | null;
      reply_to_id: number | null;
      reply_preview: string | null;
      reply_author: string | null;
      edited_at: string | null;
      is_deleted: boolean;
      created_at: string;
    }

    export interface PostAuthor {
      id: number;
      username: string;
      display_name: string | null;
      avatar_color: string | null;
    }

    export interface Post {
      id: number;
      author: PostAuthor;
      text: string | null;
      attachment: Attachment | null;
      is_deleted: boolean;
      created_at: string;
      likes_count: number;
      comments_count: number;
      is_liked: boolean;
      is_mine: boolean;
    }

    export interface PostComment {
      id: number;
      post_id: number;
      author: PostAuthor;
      text: string;
      created_at: string;
    }
''')

T["frontend/src/PostCard.tsx"] = _t('''
    import { useEffect, useState } from "react";
    import Avatar from "./Avatar";
    import { api, fileUrl } from "./api";
    import type { Post, PostComment } from "./types";

    function timeAgo(iso: string): string {
      const d = new Date(iso);
      const diff = (Date.now() - d.getTime()) / 1000;
      if (diff < 60) return "только что";
      if (diff < 3600) return `${Math.floor(diff / 60)} мин`;
      if (diff < 86400) return `${Math.floor(diff / 3600)} ч`;
      if (diff < 604800) return `${Math.floor(diff / 86400)} дн`;
      return d.toLocaleDateString();
    }

    export default function PostCard({
      post, currentUserId, onOpenProfile, onDelete, onUpdate
    }: {
      post: Post;
      currentUserId: number;
      onOpenProfile: (userId: number) => void;
      onDelete: (postId: number) => void;
      onUpdate: (p: Post) => void;
    }) {
      const [showComments, setShowComments] = useState(false);
      const [comments, setComments] = useState<PostComment[]>([]);
      const [commentText, setCommentText] = useState("");
      const [likeAnim, setLikeAnim] = useState(false);
      const [lightbox, setLightbox] = useState<string | null>(null);

      useEffect(() => {
        if (!showComments) return;
        api.get<PostComment[]>(`/posts/${post.id}/comments`).then((r) => setComments(r.data));
      }, [showComments, post.id]);

      const toggleLike = async () => {
        if (post.is_liked) {
          await api.delete(`/posts/${post.id}/like`);
          onUpdate({ ...post, is_liked: false, likes_count: post.likes_count - 1 });
        } else {
          await api.post(`/posts/${post.id}/like`);
          setLikeAnim(true);
          setTimeout(() => setLikeAnim(false), 400);
          onUpdate({ ...post, is_liked: true, likes_count: post.likes_count + 1 });
        }
      };

      const sendComment = async () => {
        const t = commentText.trim();
        if (!t) return;
        const { data } = await api.post<PostComment>(`/posts/${post.id}/comments`, { text: t });
        setComments((prev) => [...prev, data]);
        setCommentText("");
        onUpdate({ ...post, comments_count: post.comments_count + 1 });
      };

      const deleteComment = async (id: number) => {
        if (!confirm("Удалить комментарий?")) return;
        await api.delete(`/posts/comments/${id}`);
        setComments((prev) => prev.filter((c) => c.id !== id));
        onUpdate({ ...post, comments_count: post.comments_count - 1 });
      };

      const author = {
        username: post.author.username,
        display_name: post.author.display_name,
        avatar_color: post.author.avatar_color,
      };

      const isImage = post.attachment && post.attachment.content_type.startsWith("image/");

      return (
        <article className="mb-4 overflow-hidden rounded-2xl bg-white shadow-sm dark:bg-tg-side">
          <header className="flex items-center gap-3 p-3">
            <button onClick={() => onOpenProfile(post.author.id)}>
              <Avatar user={author} size={40} />
            </button>
            <div className="min-w-0 flex-1">
              <button
                onClick={() => onOpenProfile(post.author.id)}
                className="truncate font-semibold text-slate-800 hover:underline dark:text-slate-100"
              >
                {post.author.display_name || post.author.username}
              </button>
              <div className="text-xs text-slate-500">
                @{post.author.username} · {timeAgo(post.created_at)}
              </div>
            </div>
            {post.is_mine && !post.is_deleted && (
              <button
                onClick={() => onDelete(post.id)}
                title="Удалить"
                className="rounded-full p-2 text-slate-400 hover:bg-slate-100 hover:text-red-500 dark:hover:bg-slate-800"
              >
                ✕
              </button>
            )}
          </header>

          {post.text && (
            <div className="whitespace-pre-wrap break-words px-3 pb-3 text-sm text-slate-800 dark:text-slate-100">
              {post.text}
            </div>
          )}

          {isImage && post.attachment && (
            <img
              src={fileUrl(post.attachment.id)}
              alt=""
              onClick={() => setLightbox(fileUrl(post.attachment!.id))}
              className="max-h-[600px] w-full cursor-pointer object-cover"
            />
          )}

          {post.attachment && !isImage && (
            <a
              href={fileUrl(post.attachment.id)}
              target="_blank"
              rel="noreferrer"
              className="mx-3 mb-3 flex items-center gap-3 rounded-xl border border-slate-200 p-3 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              <span className="text-2xl">📎</span>
              <span className="truncate text-sm text-slate-700 dark:text-slate-200">
                {post.attachment.filename}
              </span>
            </a>
          )}

          <div className="flex items-center gap-1 border-t border-slate-100 px-3 py-2 dark:border-slate-800">
            <button
              onClick={toggleLike}
              className={
                "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition " +
                (post.is_liked
                  ? "text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                  : "text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800")
              }
            >
              <span className={likeAnim ? "inline-block animate-bounce text-lg" : "text-lg"}>
                {post.is_liked ? "❤️" : "🤍"}
              </span>
              {post.likes_count > 0 && <span>{post.likes_count}</span>}
            </button>

            <button
              onClick={() => setShowComments(!showComments)}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-500 transition hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
            >
              <span className="text-lg">💬</span>
              {post.comments_count > 0 && <span>{post.comments_count}</span>}
            </button>
          </div>

          {showComments && (
            <div className="border-t border-slate-100 bg-slate-50 p-3 dark:border-slate-800 dark:bg-tg-panel">
              {comments.map((c) => (
                <div key={c.id} className="group mb-2 flex gap-2">
                  <Avatar
                    user={{
                      username: c.author.username,
                      display_name: c.author.display_name,
                      avatar_color: c.author.avatar_color,
                    }}
                    size={32}
                  />
                  <div className="min-w-0 flex-1 rounded-xl bg-white px-3 py-2 dark:bg-tg-bubble">
                    <div className="flex items-baseline gap-2">
                      <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                        {c.author.display_name || c.author.username}
                      </span>
                      <span className="text-[10px] text-slate-400">{timeAgo(c.created_at)}</span>
                    </div>
                    <div className="whitespace-pre-wrap break-words text-sm text-slate-700 dark:text-slate-200">
                      {c.text}
                    </div>
                  </div>
                  {c.author.id === currentUserId && (
                    <button
                      onClick={() => deleteComment(c.id)}
                      className="self-start opacity-0 text-xs text-red-400 transition group-hover:opacity-100"
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}

              <div className="mt-2 flex gap-2">
                <input
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendComment()}
                  placeholder="Написать комментарий..."
                  className="flex-1 rounded-xl bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-500/30 dark:bg-tg-bubble dark:text-slate-100"
                />
                <button
                  onClick={sendComment}
                  disabled={!commentText.trim()}
                  className="rounded-xl bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50"
                >
                  →
                </button>
              </div>
            </div>
          )}

          {lightbox && (
            <div
              className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 p-4"
              onClick={() => setLightbox(null)}
            >
              <img src={lightbox} className="max-h-full max-w-full object-contain" alt="" />
            </div>
          )}
        </article>
      );
    }
''')

T["frontend/src/PostComposer.tsx"] = _t('''
    import { useRef, useState } from "react";
    import { api } from "./api";
    import type { Attachment, Post } from "./types";

    export default function PostComposer({
      onCreated, currentUser
    }: {
      onCreated: (p: Post) => void;
      currentUser: { display_name: string | null; username: string; avatar_color: string | null };
    }) {
      const [text, setText] = useState("");
      const [attachment, setAttachment] = useState<Attachment | null>(null);
      const [busy, setBusy] = useState(false);
      const fileRef = useRef<HTMLInputElement>(null);

      const pickImage = () => fileRef.current?.click();

      const upload = async (f: File) => {
        const form = new FormData();
        form.append("file", f);
        const { data } = await api.post<Attachment>("/files/upload", form, {
          headers: { "Content-Type": "multipart/form-data" }
        });
        setAttachment(data);
      };

      const submit = async () => {
        if (!text.trim() && !attachment) return;
        setBusy(true);
        try {
          const { data } = await api.post<Post>("/posts", {
            text: text.trim() || null,
            attachment_id: attachment?.id ?? null,
          });
          onCreated(data);
          setText("");
          setAttachment(null);
        } finally {
          setBusy(false);
        }
      };

      return (
        <div className="mb-4 rounded-2xl bg-white p-3 shadow-sm dark:bg-tg-side">
          <div className="flex gap-3">
            <div
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full font-semibold text-white"
              style={{ background: currentUser.avatar_color || "#4f46e5" }}
            >
              {(currentUser.display_name || currentUser.username || "?").slice(0, 1).toUpperCase()}
            </div>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Что у вас нового?"
              rows={2}
              className="flex-1 resize-none rounded-xl bg-slate-100 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-500/30 dark:bg-tg-bubble dark:text-slate-100"
            />
          </div>

          {attachment && (
            <div className="relative mt-2 ml-13">
              {attachment.content_type.startsWith("image/") ? (
                <img
                  src={`http://localhost:8000/api/v1/files/${attachment.id}?token=${localStorage.getItem("access_token")}`}
                  alt=""
                  className="max-h-64 rounded-xl object-cover"
                />
              ) : (
                <div className="rounded-xl bg-slate-100 px-3 py-2 text-sm dark:bg-tg-bubble">
                  📎 {attachment.filename}
                </div>
              )}
              <button
                onClick={() => setAttachment(null)}
                className="absolute right-2 top-2 rounded-full bg-black/60 px-2 py-1 text-xs text-white"
              >
                ✕
              </button>
            </div>
          )}

          <div className="mt-2 flex items-center justify-between">
            <div>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) upload(f);
                  if (fileRef.current) fileRef.current.value = "";
                }}
              />
              <button
                onClick={pickImage}
                className="rounded-lg px-3 py-1.5 text-lg text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
              >
                🖼
              </button>
            </div>
            <button
              onClick={submit}
              disabled={busy || (!text.trim() && !attachment)}
              className="rounded-xl bg-brand-600 px-5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-40"
            >
              {busy ? "..." : "Опубликовать"}
            </button>
          </div>
        </div>
      );
    }
''')

T["frontend/src/Feed.tsx"] = _t('''
    import { useCallback, useEffect, useState } from "react";
    import PostCard from "./PostCard";
    import PostComposer from "./PostComposer";
    import { api } from "./api";
    import type { Post, User } from "./types";

    export default function Feed({
      currentUser, onOpenProfile
    }: {
      currentUser: User;
      onOpenProfile: (userId: number) => void;
    }) {
      const [posts, setPosts] = useState<Post[]>([]);
      const [loading, setLoading] = useState(true);

      const load = useCallback(async () => {
        const { data } = await api.get<Post[]>("/posts/feed");
        setPosts(data);
        setLoading(false);
      }, []);

      useEffect(() => { load(); }, [load]);

      const handleCreated = (p: Post) => setPosts((prev) => [p, ...prev]);

      const handleUpdate = (p: Post) =>
        setPosts((prev) => prev.map((x) => (x.id === p.id ? p : x)));

      const handleDelete = async (id: number) => {
        if (!confirm("Удалить пост?")) return;
        await api.delete(`/posts/${id}`);
        setPosts((prev) => prev.filter((x) => x.id !== id));
      };

      return (
        <div className="mx-auto w-full max-w-2xl px-4 py-6">
          <PostComposer
            currentUser={{
              username: currentUser.username,
              display_name: currentUser.display_name,
              avatar_color: currentUser.avatar_color,
            }}
            onCreated={handleCreated}
          />

          {loading && (
            <div className="py-12 text-center text-slate-400">Загрузка ленты...</div>
          )}

          {!loading && posts.length === 0 && (
            <div className="rounded-2xl bg-white p-8 text-center dark:bg-tg-side">
              <div className="mb-2 text-4xl">📰</div>
              <div className="font-medium text-slate-700 dark:text-slate-200">
                Пока пусто
              </div>
              <div className="mt-1 text-sm text-slate-500">
                Подпишись на кого-нибудь или напиши первый пост
              </div>
            </div>
          )}

          {posts.map((p) => (
            <PostCard
              key={p.id}
              post={p}
              currentUserId={currentUser.id}
              onOpenProfile={onOpenProfile}
              onDelete={handleDelete}
              onUpdate={handleUpdate}
            />
          ))}
        </div>
      );
    }
''')

T["frontend/src/ProfilePage.tsx"] = _t('''
    import { useCallback, useEffect, useState } from "react";
    import Avatar from "./Avatar";
    import PostCard from "./PostCard";
    import { api } from "./api";
    import type { Post, User, UserProfile } from "./types";

    export default function ProfilePage({
      userId, currentUser, onBack, onOpenProfile, onChatWith
    }: {
      userId: number;
      currentUser: User;
      onBack: () => void;
      onOpenProfile: (id: number) => void;
      onChatWith: (userId: number) => void;
    }) {
      const [profile, setProfile] = useState<UserProfile | null>(null);
      const [posts, setPosts] = useState<Post[]>([]);
      const [loading, setLoading] = useState(true);

      const load = useCallback(async () => {
        setLoading(true);
        const [p, ps] = await Promise.all([
          api.get<UserProfile>(`/users/${userId}/profile`),
          api.get<Post[]>(`/posts/user/${userId}`),
        ]);
        setProfile(p.data);
        setPosts(ps.data);
        setLoading(false);
      }, [userId]);

      useEffect(() => { load(); }, [load]);

      const toggleFollow = async () => {
        if (!profile) return;
        if (profile.is_following) {
          await api.delete(`/users/${userId}/follow`);
          setProfile({ ...profile, is_following: false, followers_count: profile.followers_count - 1 });
        } else {
          await api.post(`/users/${userId}/follow`);
          setProfile({ ...profile, is_following: true, followers_count: profile.followers_count + 1 });
        }
      };

      const handleUpdate = (p: Post) =>
        setPosts((prev) => prev.map((x) => (x.id === p.id ? p : x)));

      const handleDelete = async (id: number) => {
        if (!confirm("Удалить пост?")) return;
        await api.delete(`/posts/${id}`);
        setPosts((prev) => prev.filter((x) => x.id !== id));
        if (profile) setProfile({ ...profile, posts_count: profile.posts_count - 1 });
      };

      if (loading || !profile) {
        return (
          <div className="flex flex-1 items-center justify-center text-slate-400">
            Загрузка...
          </div>
        );
      }

      const avatarUser = {
        username: profile.username,
        display_name: profile.display_name,
        avatar_color: profile.avatar_color,
      };

      return (
        <div className="flex-1 overflow-y-auto bg-slate-100 dark:bg-tg-bg">
          <div className="relative">
            <div
              className="h-40 w-full"
              style={{
                background: `linear-gradient(135deg, ${profile.avatar_color || "#4f46e5"} 0%, #0f172a 100%)`,
              }}
            />
            <button
              onClick={onBack}
              className="absolute left-4 top-4 rounded-full bg-black/30 px-3 py-1.5 text-sm text-white backdrop-blur hover:bg-black/50"
            >
              ← Назад
            </button>
          </div>

          <div className="mx-auto w-full max-w-2xl px-4">
            <div className="-mt-16 flex items-end gap-4">
              <div className="rounded-full border-4 border-slate-100 dark:border-tg-bg">
                <Avatar user={avatarUser} size={112} />
              </div>
              <div className="pb-2">
                <h1 className="text-2xl font-bold text-slate-800 dark:text-white">
                  {profile.display_name || profile.username}
                </h1>
                <div className="text-sm text-slate-500">@{profile.username}</div>
              </div>
            </div>

            {profile.bio && (
              <p className="mt-3 whitespace-pre-wrap text-slate-700 dark:text-slate-200">
                {profile.bio}
              </p>
            )}

            <div className="mt-4 flex gap-6 text-sm">
              <div>
                <span className="font-bold text-slate-800 dark:text-white">{profile.posts_count}</span>
                <span className="ml-1 text-slate-500">постов</span>
              </div>
              <div>
                <span className="font-bold text-slate-800 dark:text-white">{profile.followers_count}</span>
                <span className="ml-1 text-slate-500">подписчиков</span>
              </div>
              <div>
                <span className="font-bold text-slate-800 dark:text-white">{profile.following_count}</span>
                <span className="ml-1 text-slate-500">подписок</span>
              </div>
            </div>

            {!profile.is_me && (
              <div className="mt-4 flex gap-2">
                <button
                  onClick={toggleFollow}
                  className={
                    "rounded-xl px-5 py-2 text-sm font-medium transition " +
                    (profile.is_following
                      ? "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-tg-side dark:text-slate-200"
                      : "bg-brand-600 text-white hover:bg-brand-700")
                  }
                >
                  {profile.is_following ? "Отписаться" : "Подписаться"}
                </button>
                <button
                  onClick={() => onChatWith(profile.id)}
                  className="rounded-xl border border-brand-500 px-5 py-2 text-sm font-medium text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-600/10"
                >
                  Написать
                </button>
              </div>
            )}
          </div>

          <div className="mx-auto mt-6 w-full max-w-2xl px-4 pb-8">
            <h2 className="mb-3 text-sm font-semibold uppercase text-slate-500">Посты</h2>
            {posts.length === 0 && (
              <div className="rounded-2xl bg-white p-8 text-center text-slate-400 dark:bg-tg-side">
                Пока нет постов
              </div>
            )}
            {posts.map((p) => (
              <PostCard
                key={p.id}
                post={p}
                currentUserId={currentUser.id}
                onOpenProfile={onOpenProfile}
                onDelete={handleDelete}
                onUpdate={handleUpdate}
              />
            ))}
          </div>
        </div>
      );
    }
''')

T["frontend/src/ChatList.tsx"] = _t('''
    import { useMemo, useState } from "react";
    import Avatar from "./Avatar";
    import type { Chat, User } from "./types";

    function fmtTime(iso: string | null | undefined) {
      if (!iso) return "";
      const d = new Date(iso);
      const now = new Date();
      const sameDay = d.toDateString() === now.toDateString();
      if (sameDay) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      const yest = new Date(now); yest.setDate(now.getDate() - 1);
      if (d.toDateString() === yest.toDateString()) return "Вчера";
      return d.toLocaleDateString([], { day: "2-digit", month: "2-digit" });
    }

    function chatTitle(c: Chat) {
      if (c.peer) return c.peer.display_name || c.peer.username;
      return c.title || `Чат #${c.id}`;
    }

    function chatSubtitle(c: Chat) {
      const lm = c.last_message;
      if (!lm) return "Нет сообщений";
      if (lm.message_type === "system") return lm.text || "";
      const who = c.is_group ? `${lm.author_display || lm.author_username}: ` : "";
      let body = lm.text || "";
      if (lm.message_type === "image") body = "📷 Фото";
      else if (lm.message_type === "voice") body = "🎤 Голосовое";
      else if (lm.message_type === "file") body = `📎 ${lm.attachment?.filename || "Файл"}`;
      else if (lm.message_type === "sticker") body = lm.text || "Стикер";
      return who + body;
    }

    export default function ChatList({
      chats, activeId, onSelect, onlineUsers, currentUser, onOpenProfile, onOpenSettings,
      onOpenFeed, onOpenMyProfile, mode
    }: {
      chats: Chat[];
      activeId: number | null;
      onSelect: (id: number) => void;
      onlineUsers: Set<number>;
      currentUser: User;
      onOpenProfile: () => void;
      onOpenSettings: () => void;
      onOpenFeed: () => void;
      onOpenMyProfile: () => void;
      mode: "chats" | "feed" | "profile";
    }) {
      const [query, setQuery] = useState("");

      const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return chats;
        return chats.filter((c) => {
          const t = chatTitle(c).toLowerCase();
          const s = chatSubtitle(c).toLowerCase();
          return t.includes(q) || s.includes(q);
        });
      }, [chats, query]);

      return (
        <aside className="flex w-80 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-tg-side">
          <div className="flex items-center gap-2 p-3">
            <button onClick={onOpenProfile} title="Настройки профиля">
              <Avatar user={currentUser} size={40} />
            </button>
            <div className="relative flex-1">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Поиск"
                className="w-full rounded-full bg-slate-100 px-4 py-2 text-sm outline-none transition focus:ring-2 focus:ring-brand-500/30 dark:bg-tg-bubble dark:text-slate-100"
              />
            </div>
            <button
              onClick={onOpenSettings}
              title="Настройки"
              className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 dark:hover:bg-slate-700 dark:text-slate-300"
            >
              ⚙
            </button>
          </div>

          <div className="flex gap-1 border-b border-slate-200 px-2 pb-2 dark:border-slate-800">
            <button
              onClick={onOpenFeed}
              className={
                "flex-1 rounded-lg py-2 text-sm font-medium transition " +
                (mode === "feed"
                  ? "bg-brand-600 text-white"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800")
              }
            >
              📰 Лента
            </button>
            <button
              onClick={onOpenMyProfile}
              className={
                "flex-1 rounded-lg py-2 text-sm font-medium transition " +
                (mode === "profile"
                  ? "bg-brand-600 text-white"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800")
              }
            >
              👤 Профиль
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            {filtered.length === 0 && (
              <div className="p-6 text-center text-sm text-slate-400">
                {query ? "Ничего не найдено" : "Пока нет чатов"}
              </div>
            )}
            {filtered.map((c) => {
              const active = c.id === activeId && mode === "chats";
              const peerOnline = c.peer ? onlineUsers.has(c.peer.id) : false;
              const avatarUser = c.peer || {
                username: c.title || "G",
                display_name: c.title || "Group",
                avatar_color: c.avatar_color || "#64748b",
              };
              return (
                <button
                  key={c.id}
                  onClick={() => onSelect(c.id)}
                  className={
                    "flex w-full items-center gap-3 border-b border-slate-100 px-3 py-2 text-left transition dark:border-slate-800 " +
                    (active
                      ? "bg-brand-500 text-white dark:bg-tg-accent/30"
                      : "hover:bg-slate-50 dark:hover:bg-slate-800/50")
                  }
                >
                  <Avatar user={avatarUser as any} size={48} showOnline={!!c.peer} online={peerOnline} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="truncate font-medium text-slate-800 dark:text-slate-100">
                        {chatTitle(c)}
                      </span>
                      <span className={
                        "shrink-0 text-[11px] " +
                        (active ? "text-white/80" : "text-slate-400 dark:text-slate-500")
                      }>
                        {fmtTime(c.last_message?.created_at || c.created_at)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className={
                        "truncate text-sm " +
                        (active ? "text-white/90" : "text-slate-500 dark:text-slate-400")
                      }>
                        {chatSubtitle(c)}
                      </span>
                      {c.unread_count > 0 && !active && (
                        <span className="shrink-0 rounded-full bg-brand-600 px-2 py-0.5 text-[11px] font-medium text-white">
                          {c.unread_count}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </aside>
      );
    }
''')

T["frontend/src/ChatWindow.tsx"] = _t('''
    import { useEffect, useMemo, useRef, useState } from "react";
    import Avatar from "./Avatar";
    import MessageBubble from "./MessageBubble";
    import EmojiPicker from "./EmojiPicker";
    import StickerPicker from "./StickerPicker";
    import FileUpload from "./FileUpload";
    import VoiceRecorder from "./VoiceRecorder";
    import Lightbox from "./Lightbox";
    import { api } from "./api";
    import type { Chat, Message, User } from "./types";

    function dayLabel(iso: string) {
      const d = new Date(iso);
      const now = new Date();
      if (d.toDateString() === now.toDateString()) return "Сегодня";
      const y = new Date(now); y.setDate(now.getDate() - 1);
      if (d.toDateString() === y.toDateString()) return "Вчера";
      return d.toLocaleDateString([], { day: "numeric", month: "long" });
    }

    export default function ChatWindow({
      chat, currentUser, send, subscribe, onlineUsers, onOpenInfo, onOpenUser
    }: {
      chat: Chat;
      currentUser: User;
      send: (data: any) => void;
      subscribe: (h: (d: any) => void) => () => void;
      onlineUsers: Set<number>;
      onOpenInfo: () => void;
      onOpenUser: (userId: number) => void;
    }) {
      const [messages, setMessages] = useState<Message[]>([]);
      const [text, setText] = useState("");
      const [replyTo, setReplyTo] = useState<Message | null>(null);
      const [editing, setEditing] = useState<Message | null>(null);
      const [emojiOpen, setEmojiOpen] = useState(false);
      const [stickerOpen, setStickerOpen] = useState(false);
      const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());
      const [peerReadUpTo, setPeerReadUpTo] = useState<number>(0);
      const [lightbox, setLightbox] = useState<string | null>(null);
      const bottomRef = useRef<HTMLDivElement>(null);
      const typingTimeout = useRef<number | null>(null);
      const lastTypingSent = useRef<number>(0);

      useEffect(() => {
        api.get<Message[]>(`/chats/${chat.id}/messages`).then((r) => setMessages(r.data));
        send({ type: "subscribe", chat_id: chat.id });
        api.post(`/chats/${chat.id}/read`).catch(() => {});
        return () => send({ type: "unsubscribe", chat_id: chat.id });
      }, [chat.id]);

      useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "auto" });
      }, [messages.length]);

      useEffect(() => {
        const last = messages[messages.length - 1];
        if (!last) return;
        if (last.author_id !== currentUser.id && last.message_type !== "system") {
          send({ type: "read", chat_id: chat.id, message_id: last.id });
        }
      }, [messages.length]);

      useEffect(() => {
        const off = subscribe((d) => {
          if (d.type === "message" && d.chat_id === chat.id) {
            setMessages((prev) => {
              if (prev.some((m) => m.id === d.id)) return prev;
              return [...prev, {
                id: d.id, chat_id: d.chat_id,
                author_id: d.author_id, author_username: d.author_username,
                author_display: d.author_display, author_avatar_color: d.author_avatar_color,
                text: d.text, message_type: d.message_type || "text",
                attachment: d.attachment || null,
                reply_to_id: d.reply_to_id,
                reply_preview: d.reply_preview, reply_author: d.reply_author,
                edited_at: null, is_deleted: false, created_at: d.created_at,
              }];
            });
            if (d.author_id !== currentUser.id && d.message_type !== "system") {
              send({ type: "read", chat_id: chat.id, message_id: d.id });
            }
          } else if (d.type === "message_edited" && d.chat_id === chat.id) {
            setMessages((prev) =>
              prev.map((m) => m.id === d.message_id ? { ...m, text: d.text, edited_at: d.edited_at } : m)
            );
          } else if (d.type === "message_deleted" && d.chat_id === chat.id) {
            setMessages((prev) =>
              prev.map((m) => m.id === d.message_id ? { ...m, is_deleted: true, text: "Сообщение удалено" } : m)
            );
          } else if (d.type === "typing" && d.chat_id === chat.id) {
            setTypingUsers((prev) => {
              const next = new Set(prev);
              if (d.is_typing) next.add(d.username);
              else next.delete(d.username);
              return next;
            });
          } else if (d.type === "read" && d.chat_id === chat.id) {
            setPeerReadUpTo((prev) => Math.max(prev, d.message_id));
          }
        });
        return off;
      }, [chat.id, currentUser.id, subscribe, send]);

      const grouped = useMemo(() => {
        const out: { day: string; items: Message[] }[] = [];
        for (const m of messages) {
          const day = dayLabel(m.created_at);
          const last = out[out.length - 1];
          if (last && last.day === day) last.items.push(m);
          else out.push({ day, items: [m] });
        }
        return out;
      }, [messages]);

      const doSend = () => {
        const t = text.trim();
        if (!t) return;
        if (editing) {
          send({ type: "edit", message_id: editing.id, text: t });
          setEditing(null);
        } else {
          send({ type: "send", chat_id: chat.id, text: t, reply_to_id: replyTo?.id ?? null, message_type: "text" });
          setReplyTo(null);
        }
        setText("");
        send({ type: "typing", chat_id: chat.id, is_typing: false });
      };

      const sendAttachment = (attachmentId: number, type: "image" | "file" | "voice") => {
        send({
          type: "send", chat_id: chat.id, text: null,
          message_type: type, attachment_id: attachmentId,
          reply_to_id: replyTo?.id ?? null,
        });
        setReplyTo(null);
      };

      const sendSticker = (sticker: string) => {
        send({
          type: "send", chat_id: chat.id, text: sticker,
          message_type: "sticker", reply_to_id: replyTo?.id ?? null,
        });
        setStickerOpen(false);
        setReplyTo(null);
      };

      const onKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          doSend();
        }
      };

      const onTextChange = (v: string) => {
        setText(v);
        const now = Date.now();
        if (now - lastTypingSent.current > 2000) {
          send({ type: "typing", chat_id: chat.id, is_typing: true });
          lastTypingSent.current = now;
        }
        if (typingTimeout.current) window.clearTimeout(typingTimeout.current);
        typingTimeout.current = window.setTimeout(() => {
          send({ type: "typing", chat_id: chat.id, is_typing: false });
        }, 3000);
      };

      const peerOnline = chat.peer ? onlineUsers.has(chat.peer.id) : false;
      const headerTitle = chat.peer
        ? chat.peer.display_name || chat.peer.username
        : chat.title || `Чат #${chat.id}`;
      const headerSub = typingUsers.size > 0
        ? "печатает…"
        : chat.peer
        ? (peerOnline ? "в сети" : "не в сети")
        : `${chat.member_count} участников`;

      const avatarUser = chat.peer || {
        username: chat.title || "G",
        display_name: chat.title || "Group",
        avatar_color: chat.avatar_color || "#64748b",
      };

      return (
        <main className="flex flex-1 flex-col bg-slate-100 dark:bg-tg-bg">
          <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-2 dark:border-slate-800 dark:bg-tg-side">
            <button
              onClick={() => chat.peer ? onOpenUser(chat.peer.id) : onOpenInfo()}
              className="flex min-w-0 flex-1 items-center gap-3 transition hover:opacity-90"
            >
              <Avatar user={avatarUser as any} size={40} showOnline={!!chat.peer} online={peerOnline} />
              <div className="min-w-0 flex-1 text-left">
                <div className="truncate font-medium text-slate-800 dark:text-slate-100">
                  {headerTitle}
                </div>
                <div className="truncate text-xs text-slate-500 dark:text-slate-400">
                  {headerSub}
                </div>
              </div>
            </button>
            {chat.is_group && (
              <button
                onClick={onOpenInfo}
                className="rounded-full p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700"
                title="Информация о группе"
              >
                ℹ
              </button>
            )}
          </header>

          <div className="flex-1 overflow-y-auto px-4 py-4">
            {grouped.map((g) => (
              <div key={g.day} className="mb-4">
                <div className="mb-3 text-center">
                  <span className="rounded-full bg-slate-200/80 px-3 py-1 text-xs text-slate-600 dark:bg-tg-panel dark:text-slate-400">
                    {g.day}
                  </span>
                </div>
                <div className="space-y-1">
                  {g.items.map((m, idx) => {
                    const prev = g.items[idx - 1];
                    const showAvatar = !prev || prev.author_id !== m.author_id || prev.message_type === "system";
                    const isLast = idx === g.items.length - 1 || g.items[idx + 1].author_id !== m.author_id;
                    return (
                      <MessageBubble
                        key={m.id}
                        msg={m}
                        mine={m.author_id === currentUser.id}
                        showAvatar={showAvatar}
                        isLast={isLast}
                        readByPeer={peerReadUpTo >= m.id}
                        onReply={(mm) => { setReplyTo(mm); setEditing(null); }}
                        onEdit={(mm) => { setEditing(mm); setReplyTo(null); setText(mm.text || ""); }}
                        onDelete={(mm) => send({ type: "delete", message_id: mm.id })}
                        onOpenImage={(url) => setLightbox(url)}
                        onOpenProfile={onOpenUser}
                      />
                    );
                  })}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {(replyTo || editing) && (
            <div className="flex items-center gap-2 border-t border-slate-200 bg-white px-4 py-2 dark:border-slate-800 dark:bg-tg-side">
              <div className="flex-1 truncate border-l-2 border-brand-500 pl-2 text-sm">
                <div className="text-xs font-medium text-brand-600">
                  {editing ? "Редактирование" : `Ответ ${replyTo?.author_display || replyTo?.author_username}`}
                </div>
                <div className="truncate text-slate-500 dark:text-slate-400">
                  {editing ? editing.text : replyTo?.text}
                </div>
              </div>
              <button
                onClick={() => { setReplyTo(null); setEditing(null); setText(""); }}
                className="rounded-full p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700"
              >
                ✕
              </button>
            </div>
          )}

          <div className="relative border-t border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-tg-side">
            {typingUsers.size > 0 && (
              <div className="absolute -top-5 left-4 flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                <span className="typing-dot inline-block h-1.5 w-1.5 rounded-full bg-slate-500" />
                <span className="typing-dot inline-block h-1.5 w-1.5 rounded-full bg-slate-500" />
                <span className="typing-dot inline-block h-1.5 w-1.5 rounded-full bg-slate-500" />
                <span className="ml-1">{Array.from(typingUsers).join(", ")}</span>
              </div>
            )}
            <div className="flex items-end gap-1">
              <FileUpload asType="image" accept="image/*" onUploaded={(a, t) => sendAttachment(a.id, t)} />
              <FileUpload asType="file" onUploaded={(a, t) => sendAttachment(a.id, t)} />
              <button
                onClick={() => { setStickerOpen(!stickerOpen); setEmojiOpen(false); }}
                className="rounded-full p-2 text-xl leading-none transition hover:bg-slate-100 dark:hover:bg-slate-700"
              >
                🐱
              </button>
              <button
                onClick={() => { setEmojiOpen(!emojiOpen); setStickerOpen(false); }}
                className="rounded-full p-2 text-xl leading-none transition hover:bg-slate-100 dark:hover:bg-slate-700"
              >
                😊
              </button>
              <textarea
                value={text}
                onChange={(e) => onTextChange(e.target.value)}
                onKeyDown={onKeyDown}
                rows={1}
                placeholder="Написать сообщение..."
                className="max-h-32 flex-1 resize-none rounded-2xl bg-slate-100 px-4 py-2 text-sm outline-none transition focus:ring-2 focus:ring-brand-500/30 dark:bg-tg-bubble dark:text-slate-100"
              />
              <VoiceRecorder onUploaded={(a) => sendAttachment(a.id, "voice")} />
              <button
                onClick={doSend}
                disabled={!text.trim()}
                className="rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-40"
              >
                ➤
              </button>
            </div>

            {emojiOpen && <EmojiPicker onPick={(e) => setText((t) => t + e)} onClose={() => setEmojiOpen(false)} />}
            {stickerOpen && <StickerPicker onPick={sendSticker} onClose={() => setStickerOpen(false)} />}
          </div>

          {lightbox && <Lightbox src={lightbox} onClose={() => setLightbox(null)} />}
        </main>
      );
    }
''')

T["frontend/src/MessageBubble.tsx"] = _t('''
    import { useState } from "react";
    import Avatar from "./Avatar";
    import { fileUrl, humanSize } from "./api";
    import type { Message, User } from "./types";

    function iconFor(mime: string): string {
      if (mime.startsWith("image/")) return "🖼";
      if (mime.startsWith("audio/")) return "🎵";
      if (mime.startsWith("video/")) return "🎬";
      if (mime.includes("pdf")) return "📕";
      if (mime.includes("zip") || mime.includes("tar")) return "🗜";
      if (mime.includes("word") || mime.includes("document")) return "📘";
      if (mime.includes("sheet") || mime.includes("excel")) return "📗";
      return "📎";
    }

    function fmtDuration(sec: number): string {
      const m = Math.floor(sec / 60);
      const s = Math.floor(sec % 60);
      return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    }

    export default function MessageBubble({
      msg, mine, showAvatar, isLast, onReply, onEdit, onDelete, readByPeer, onOpenImage, onOpenProfile
    }: {
      msg: Message;
      mine: boolean;
      showAvatar: boolean;
      isLast: boolean;
      onReply: (m: Message) => void;
      onEdit: (m: Message) => void;
      onDelete: (m: Message) => void;
      readByPeer: boolean;
      onOpenImage: (url: string) => void;
      onOpenProfile: (userId: number) => void;
    }) {
      const [menuOpen, setMenuOpen] = useState(false);
      const [audioPlaying, setAudioPlaying] = useState(false);
      const [audioCurrent, setAudioCurrent] = useState(0);
      const [audioDuration, setAudioDuration] = useState(0);

      if (msg.message_type === "system") {
        return (
          <div className="my-2 flex justify-center">
            <span className="rounded-full bg-slate-200/70 px-3 py-1 text-xs text-slate-600 dark:bg-tg-panel dark:text-slate-400">
              {msg.text}
            </span>
          </div>
        );
      }

      const author: Pick<User, "username" | "display_name" | "avatar_color"> = {
        username: msg.author_username,
        display_name: msg.author_display,
        avatar_color: msg.author_avatar_color,
      };

      const bubbleColor = mine
        ? "bg-brand-600 text-white"
        : "bg-white text-slate-800 dark:bg-tg-bubble dark:text-slate-100";

      const radius = isLast
        ? mine
          ? "rounded-2xl rounded-br-sm"
          : "rounded-2xl rounded-bl-sm"
        : "rounded-2xl";

      const isSticker = msg.message_type === "sticker" && !msg.is_deleted;
      const isImage = msg.message_type === "image" && msg.attachment && !msg.is_deleted;
      const isVoice = msg.message_type === "voice" && msg.attachment && !msg.is_deleted;
      const isFile = msg.message_type === "file" && msg.attachment && !msg.is_deleted;

      if (isSticker) {
        return (
          <div className={"group flex gap-2 " + (mine ? "flex-row-reverse" : "")}>
            {!mine ? (
              <button className="w-8 shrink-0" onClick={() => onOpenProfile(msg.author_id)}>
                {showAvatar && <Avatar user={author} size={32} />}
              </button>
            ) : null}
            <div className="relative">
              <div className="animate-pop text-7xl leading-none">{msg.text}</div>
              <div className={"mt-0.5 flex items-center gap-1 text-[10px] " + (mine ? "justify-end" : "")}>
                <span className="text-slate-400">
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
                {mine && (
                  <span className={readByPeer ? "text-sky-500" : "text-slate-400"}>
                    {readByPeer ? "✓✓" : "✓"}
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      }

      return (
        <div className={"group flex gap-2 " + (mine ? "flex-row-reverse" : "")}>
          {!mine ? (
            <button className="w-8 shrink-0" onClick={() => onOpenProfile(msg.author_id)}>
              {showAvatar && <Avatar user={author} size={32} />}
            </button>
          ) : null}

          <div className={"relative max-w-[70%] " + (mine ? "items-end" : "items-start")}>
            {!mine && showAvatar && (
              <button
                onClick={() => onOpenProfile(msg.author_id)}
                className="mb-0.5 ml-2 text-xs font-medium text-brand-600 hover:underline dark:text-brand-500"
              >
                {msg.author_display || msg.author_username}
              </button>
            )}

            <div className={
              "animate-pop relative overflow-hidden text-sm shadow-sm " +
              bubbleColor + " " + radius + (isImage ? "" : " px-3 py-2")
            }>
              {msg.reply_to_id && !msg.is_deleted && (
                <div className={
                  "mx-2 mb-1 mt-2 rounded border-l-2 px-2 py-1 text-xs " +
                  (mine ? "border-white/60 bg-white/10" : "border-brand-500 bg-slate-50 dark:bg-slate-800")
                }>
                  <div className="font-medium opacity-90">{msg.reply_author || "?"}</div>
                  <div className="truncate opacity-75">{msg.reply_preview || "..."}</div>
                </div>
              )}

              {isImage && msg.attachment && (
                <img
                  src={fileUrl(msg.attachment.id)}
                  alt={msg.attachment.filename}
                  onClick={() => onOpenImage(fileUrl(msg.attachment!.id))}
                  className="block max-h-80 w-full cursor-pointer object-cover"
                />
              )}

              {isVoice && msg.attachment && (
                <div className="flex items-center gap-2 px-2 py-3" style={{ minWidth: 220 }}>
                  <button
                    onClick={() => {
                      const prev = (window as any).__voiceAudio as HTMLAudioElement;
                      if (prev && prev.dataset.id === String(msg.attachment!.id)) {
                        if (prev.paused) prev.play(); else prev.pause();
                        return;
                      }
                      if (prev) prev.pause();
                      const el = new Audio(fileUrl(msg.attachment!.id));
                      (window as any).__voiceAudio = el;
                      el.dataset.id = String(msg.attachment!.id);
                      el.ontimeupdate = () => setAudioCurrent(el.currentTime);
                      el.onloadedmetadata = () => setAudioDuration(el.duration);
                      el.onplay = () => setAudioPlaying(true);
                      el.onpause = () => setAudioPlaying(false);
                      el.onended = () => { setAudioPlaying(false); setAudioCurrent(0); };
                      el.play();
                    }}
                    className={
                      "flex h-9 w-9 shrink-0 items-center justify-center rounded-full " +
                      (mine ? "bg-white/20" : "bg-brand-600 text-white")
                    }
                  >
                    {audioPlaying ? "❚❚" : "▶"}
                  </button>
                  <div className="flex-1 text-xs">
                    <div className="flex items-center gap-1">
                      <span className="text-2xl">🎤</span>
                      <span className="font-mono">
                        {fmtDuration(audioPlaying ? audioCurrent : (audioDuration || 0))}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {isFile && msg.attachment && (
                <a
                  href={fileUrl(msg.attachment.id)}
                  target="_blank"
                  rel="noreferrer"
                  className={
                    "flex items-center gap-3 px-2 py-3 transition " +
                    (mine ? "hover:bg-white/10" : "hover:bg-slate-50 dark:hover:bg-slate-800")
                  }
                >
                  <div className="text-3xl">{iconFor(msg.attachment.content_type)}</div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium">{msg.attachment.filename}</div>
                    <div className={"text-xs " + (mine ? "text-white/70" : "text-slate-500")}>
                      {humanSize(msg.attachment.size)}
                    </div>
                  </div>
                </a>
              )}

              {!isImage && !isVoice && !isFile && (
                <div className={msg.is_deleted ? "italic opacity-60" : "whitespace-pre-wrap break-words"}>
                  {msg.text}
                </div>
              )}

              <div className="mt-0.5 flex items-center justify-end gap-1 px-1 text-[10px]">
                {msg.edited_at && <span className="opacity-70">изм.</span>}
                <span className={mine ? "text-white/70" : "text-slate-400"}>
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
                {mine && !msg.is_deleted && (
                  <span className={readByPeer ? "text-sky-200" : "text-white/60"}>
                    {readByPeer ? "✓✓" : "✓"}
                  </span>
                )}
              </div>
            </div>

            {!msg.is_deleted && (
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className={
                  "absolute top-1 hidden rounded-full bg-white/90 px-1.5 py-0.5 text-xs text-slate-600 shadow group-hover:block dark:bg-slate-700 dark:text-slate-200 " +
                  (mine ? "-left-6" : "-right-6")
                }
              >
                ⋮
              </button>
            )}

            {menuOpen && (
              <div className={
                "absolute z-20 mt-1 w-32 overflow-hidden rounded-lg border border-slate-200 bg-white text-sm shadow-xl dark:border-slate-700 dark:bg-tg-panel " +
                (mine ? "right-0" : "left-0")
              }>
                <button
                  onClick={() => { onReply(msg); setMenuOpen(false); }}
                  className="block w-full px-3 py-1.5 text-left hover:bg-slate-100 dark:hover:bg-slate-700"
                >
                  Ответить
                </button>
                {mine && msg.message_type === "text" && (
                  <button
                    onClick={() => { onEdit(msg); setMenuOpen(false); }}
                    className="block w-full px-3 py-1.5 text-left hover:bg-slate-100 dark:hover:bg-slate-700"
                  >
                    Изменить
                  </button>
                )}
                {mine && (
                  <button
                    onClick={() => { onDelete(msg); setMenuOpen(false); }}
                    className="block w-full px-3 py-1.5 text-left text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
                  >
                    Удалить
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      );
    }
''')

T["frontend/src/App.tsx"] = _t('''
    import { useCallback, useEffect, useState } from "react";
    import Login from "./Login";
    import ChatList from "./ChatList";
    import ChatWindow from "./ChatWindow";
    import ProfileModal from "./ProfileModal";
    import SettingsPanel from "./SettingsPanel";
    import GroupInfoPanel from "./GroupInfoPanel";
    import Feed from "./Feed";
    import ProfilePage from "./ProfilePage";
    import { api } from "./api";
    import { useWebSocket } from "./ws";
    import type { Chat, User } from "./types";

    type Mode = "chats" | "feed" | "profile";

    export default function App() {
      const [user, setUser] = useState<User | null>(null);
      const [chats, setChats] = useState<Chat[]>([]);
      const [activeChatId, setActiveChatId] = useState<number | null>(null);
      const [loading, setLoading] = useState(true);
      const [onlineUsers, setOnlineUsers] = useState<Set<number>>(new Set());
      const [showProfile, setShowProfile] = useState(false);
      const [showSettings, setShowSettings] = useState(false);
      const [showGroupInfo, setShowGroupInfo] = useState(false);
      const [theme, setTheme] = useState<"light" | "dark">(
        (localStorage.getItem("theme") as "light" | "dark") || "light"
      );
      const [mode, setMode] = useState<Mode>("chats");
      const [profileUserId, setProfileUserId] = useState<number | null>(null);

      useEffect(() => {
        document.documentElement.classList.toggle("dark", theme === "dark");
        localStorage.setItem("theme", theme);
      }, [theme]);

      const onWs = useCallback((d: any) => {
        if (d.type === "presence") {
          setOnlineUsers((prev) => {
            const next = new Set(prev);
            if (d.online) next.add(d.user_id);
            else next.delete(d.user_id);
            return next;
          });
        } else if (d.type === "message") {
          setChats((prev) => prev.map((c) =>
            c.id === d.chat_id
              ? {
                  ...c,
                  last_message: { ...c.last_message, ...d } as any,
                  unread_count: c.id === activeChatId || d.author_id === user?.id || d.message_type === "system"
                    ? c.unread_count
                    : c.unread_count + 1,
                }
              : c
          ));
        }
      }, [activeChatId, user?.id]);

      const { send, subscribe } = useWebSocket(onWs);

      const refreshChats = useCallback(async () => {
        const { data } = await api.get<Chat[]>("/chats");
        setChats(data);
      }, []);

      const loadMe = useCallback(async () => {
        try {
          const me = await api.get<User>("/auth/me");
          setUser(me.data);
          await refreshChats();
        } catch {
          setUser(null);
          localStorage.removeItem("access_token");
        } finally {
          setLoading(false);
        }
      }, [refreshChats]);

      useEffect(() => {
        loadMe();
        const logout = () => setUser(null);
        window.addEventListener("auth:logout", logout);
        return () => window.removeEventListener("auth:logout", logout);
      }, [loadMe]);

      useEffect(() => {
        if (!user) return;
        const params = new URLSearchParams(window.location.search);
        const invite = params.get("invite");
        if (!invite) return;
        api.post<Chat>(`/chats/join/${invite}`).then((r) => {
          refreshChats().then(() => {
            setActiveChatId(r.data.id);
            setMode("chats");
          });
          window.history.replaceState({}, "", "/");
        }).catch(() => {
          window.history.replaceState({}, "", "/");
        });
      }, [user, refreshChats]);

      useEffect(() => {
        if (activeChatId !== null && mode === "chats") {
          api.post(`/chats/${activeChatId}/read`).then(() => refreshChats()).catch(() => {});
        }
      }, [activeChatId, refreshChats, mode]);

      const logout = () => {
        localStorage.removeItem("access_token");
        setUser(null);
        setChats([]);
        setActiveChatId(null);
        setMode("chats");
        setProfileUserId(null);
      };

      const openProfile = (userId: number) => {
        setProfileUserId(userId);
        setMode("profile");
      };

      const chatWithUser = async (userId: number) => {
        try {
          const { data: profile } = await api.get<{ username: string }>(`/users/${userId}/profile`);
          const { data } = await api.post<Chat>("/chats", {
            is_group: false,
            member_usernames: [profile.username],
          });
          const all = await api.get<Chat[]>("/chats");
          setChats(all.data);
          setActiveChatId(data.id);
          setMode("chats");
        } catch {}
      };

      if (loading) {
        return (
          <div className="flex h-screen items-center justify-center bg-slate-100 text-slate-500 dark:bg-tg-bg dark:text-slate-400">
            Загрузка...
          </div>
        );
      }

      if (!user) return <Login onLogin={loadMe} />;

      const activeChat = chats.find((c) => c.id === activeChatId) || null;

      return (
        <div className="flex h-screen bg-slate-100 dark:bg-tg-bg">
          <ChatList
            chats={chats}
            activeId={activeChatId}
            onSelect={(id) => { setActiveChatId(id); setMode("chats"); }}
            onlineUsers={onlineUsers}
            currentUser={user}
            onOpenProfile={() => setShowProfile(true)}
            onOpenSettings={() => setShowSettings(true)}
            onOpenFeed={() => setMode("feed")}
            onOpenMyProfile={() => { setProfileUserId(user.id); setMode("profile"); }}
            mode={mode}
          />

          {mode === "chats" && (
            activeChat ? (
              <ChatWindow
                key={activeChat.id}
                chat={activeChat}
                currentUser={user}
                send={send}
                subscribe={subscribe}
                onlineUsers={onlineUsers}
                onOpenInfo={() => setShowGroupInfo(true)}
                onOpenUser={openProfile}
              />
            ) : (
              <div className="flex flex-1 flex-col items-center justify-center text-slate-400 dark:text-slate-500">
                <div className="mb-3 text-5xl">💬</div>
                <div className="text-lg">Выберите чат</div>
                <button
                  onClick={() => setShowSettings(true)}
                  className="mt-4 rounded-xl bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
                >
                  Начать переписку
                </button>
              </div>
            )
          )}

          {mode === "feed" && (
            <div className="flex-1 overflow-y-auto">
              <Feed currentUser={user} onOpenProfile={openProfile} />
            </div>
          )}

          {mode === "profile" && profileUserId !== null && (
            <ProfilePage
              userId={profileUserId}
              currentUser={user}
              onBack={() => { setMode("chats"); setProfileUserId(null); }}
              onOpenProfile={openProfile}
              onChatWith={chatWithUser}
            />
          )}

          {showProfile && (
            <ProfileModal
              user={user}
              onClose={() => setShowProfile(false)}
              onUpdate={(u) => { setUser(u); refreshChats(); }}
              onLogout={() => { setShowProfile(false); logout(); }}
            />
          )}

          {showSettings && (
            <SettingsPanel
              currentUser={user}
              chats={chats}
              theme={theme}
              setTheme={setTheme}
              onClose={() => setShowSettings(false)}
              onChatsChanged={setChats}
              onSelectChat={(id) => { setActiveChatId(id); setMode("chats"); }}
            />
          )}

          {showGroupInfo && activeChat && (
            <GroupInfoPanel
              chat={activeChat}
              currentUser={user}
              onClose={() => setShowGroupInfo(false)}
              onChatUpdated={(c) => { setChats((prev) => prev.map((x) => x.id === c.id ? c : x)); }}
              onLeft={() => { setActiveChatId(null); refreshChats(); }}
            />
          )}
        </div>
      );
    }
''')


def write_all(root: Path) -> tuple[int, int]:
    created = updated = 0
    for rel, content in T.items():
        target = root / rel
        existed = target.exists()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            print(f"  {'~' if existed else '+'} {rel}")
            if existed: updated += 1
            else: created += 1
        except OSError as e:
            print(f"ERR {rel}: {e}", file=sys.stderr)
    return created, updated


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    print("\nСпринт 4: посты, лайки, комментарии, подписки")
    print(f"Проект:   {root}\n")
    created, updated = write_all(root)
    print(f"\nГотово: {created} создано, {updated} обновлено\n")
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml down")
    print("  docker compose -f infra/docker-compose.yml up --build")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())