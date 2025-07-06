import sqlalchemy as sa

from h.db import Base


class UserShareflowMetadata(Base):
    __tablename__ = "user_shareflow_metadata"

    id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)

    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="cascade"),
        nullable=False,
        index=True,
    )
    user = sa.orm.relationship("User")

    shareflow_metadata_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("shareflow_metadata.id", ondelete="cascade"),
        nullable=False,
        index=True,
    )
    shareflow_metadata = sa.orm.relationship("ShareflowMetadata")

    score = sa.Column(sa.Integer, nullable=False)

    def __repr__(self):
        return (
            f"<User {self.user.username} - "
            f"{self.shareflow_metadata.task_name}- {self.score}>"
        )
