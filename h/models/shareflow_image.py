import base64

import sqlalchemy as sa

from h.db import Base


class ShareflowImage(Base):
    __tablename__ = "shareflow_image"

    id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)
    """The value of annotation.id, named here pubid following the convention of group.pubid"""

    image_data = sa.Column(sa.LargeBinary, nullable=False)  # Store binary data
    image_type = sa.Column(sa.String, nullable=False)  # Store image type (e.g., 'image/jpeg')

    shareflow = sa.orm.relationship("Shareflow", back_populates="image", uselist=False)

    def set_image(self, base64_str):
        # Split the base64 string to get the data part
        header, encoded = base64_str.split(",", 1)  # Splitting the string into header and data
        self.image_type = header.split(";")[0].split(":")[1]  # Extracting MIME type
        self.image_data = base64.b64decode(encoded)

    def get_base64(self):
        """Return stored image as a base64 string."""
        if self.image_data:
            return f"data:{self.image_type};base64,{base64.b64encode(self.image_data).decode('utf-8')}"
        return None
