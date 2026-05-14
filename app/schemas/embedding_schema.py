from pydantic import BaseModel, ConfigDict, Field

class ProcessDocumentRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "source": "half_adder.sv",
                    "text": "module half_adder(input a, input b, output sum, output carry); assign sum = a ^ b; assign carry = a & b; endmodule",
                    "file_type": "sv",
                    "topic": "digital logic",
                    "url": "",
                    "section_title": "",
                    "save_to_db": True,
                    "return_embeddings": False,
                }
            ]
        }
    )

    source: str = Field(default="", description="Source name, such as a file name.")
    text: str = Field(default="", description="Document text or HDL source code to process.")
    file_type: str = Field(default="", description="File extension, such as sv, .sv, or half_adder.sv.")
    topic: str = ""
    url: str = ""
    section_title: str = ""
    save_to_db: bool = True
    return_embeddings: bool = False
