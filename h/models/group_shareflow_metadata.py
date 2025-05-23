import sqlalchemy as sa

from h.db import Base


class GroupShareflowMetadata(Base):
    __tablename__ = "group_shareflow_metadata"

    id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)

    group_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("group.id", ondelete="cascade"),
        nullable=False,
        index=True,
    )
    group = sa.orm.relationship("Group")

    shareflow_metadata_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("shareflow_metadata.id", ondelete="cascade"),
        nullable=False,
        index=True,
    )
    shareflow_metadata = sa.orm.relationship("ShareflowMetadata")

    def __repr__(self):
        return (
            f"<Group {self.group.name} pubid: {self.group.pubid} - "
            f"{self.shareflow_metadata.task_name}>"
        )
