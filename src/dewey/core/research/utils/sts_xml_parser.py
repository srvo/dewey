import xml.etree.ElementTree as ET
from typing import List, Optional

from dewey.core.base_script import BaseScript


class STSXmlParser(BaseScript):
    """
    Parses STS XML files to extract relevant information.

    This class inherits from BaseScript and utilizes its logging and
    configuration capabilities.
    """

    def __init__(self):
        """
        Initializes the STSXmlParser with configuration from the 'sts_xml_parser' section.
        """
        super().__init__(config_section="sts_xml_parser")

    def run(self) -> None:
        """
        Placeholder for the run method.

        This method should contain the core logic of the script.
        """
        self.logger.info("STSXmlParser is running.")

    def parse_xml_file(self, xml_file_path: str) -> Optional[ET.Element]:
        """
        Parses an XML file and returns the root element.

        Args:
            xml_file_path: The path to the XML file.

        Returns:
            The root element of the XML file, or None if parsing fails.

        Raises:
            FileNotFoundError: If the XML file does not exist.
            ET.ParseError: If the XML file is not well-formed.
        """
        try:
            self.logger.info(f"Parsing XML file: {xml_file_path}")
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            self.logger.debug(f"XML file parsed successfully.")
            return root
        except FileNotFoundError:
            self.logger.error(f"XML file not found: {xml_file_path}")
            raise
        except ET.ParseError as e:
            self.logger.error(f"Error parsing XML file: {xml_file_path}: {e}")
            raise

    def extract_text_from_element(
        self, element: ET.Element, xpath: str
    ) -> Optional[str]:
        """
        Extracts text from an XML element using XPath.

        Args:
            element: The XML element to extract from.
            xpath: The XPath expression to locate the desired element.

        Returns:
            The text content of the element, or None if the element is not found.
        """
        try:
            result = element.find(xpath)
            if result is not None:
                text = result.text
                self.logger.debug(f"Extracted text from {xpath}: {text}")
                return text
            else:
                self.logger.warning(f"Element not found for XPath: {xpath}")
                return None
        except Exception as e:
            self.logger.error(f"Error extracting text from XPath {xpath}: {e}")
            return None

    def extract_all_texts_from_element(
        self, element: ET.Element, xpath: str
    ) -> List[str]:
        """
        Extracts all text elements from an XML element using XPath.

        Args:
            element: The XML element to extract from.
            xpath: The XPath expression to locate the desired elements.

        Returns:
            A list of text contents of the elements.
        """
        texts = []
        try:
            results = element.findall(xpath)
            for result in results:
                if result is not None:
                    text = result.text
                    texts.append(text)
                    self.logger.debug(f"Extracted text from {xpath}: {text}")
                else:
                    self.logger.warning(f"Element not found for XPath: {xpath}")
            return texts
        except Exception as e:
            self.logger.error(f"Error extracting text from XPath {xpath}: {e}")
            return texts

    def get_element_attribute(
        self, element: ET.Element, xpath: str, attribute: str
    ) -> Optional[str]:
        """
        Gets the value of an attribute from an XML element using XPath.

        Args:
            element: The XML element to extract from.
            xpath: The XPath expression to locate the desired element.
            attribute: The name of the attribute to retrieve.

        Returns:
            The value of the attribute, or None if the element or attribute is not found.
        """
        try:
            result = element.find(xpath)
            if result is not None:
                value = result.get(attribute)
                self.logger.debug(
                    f"Extracted attribute {attribute} from {xpath}: {value}"
                )
                return value
            else:
                self.logger.warning(f"Element not found for XPath: {xpath}")
                return None
        except Exception as e:
            self.logger.error(
                f"Error extracting attribute {attribute} from XPath {xpath}: {e}"
            )
            return None


if __name__ == "__main__":
    parser = STSXmlParser()
    parser.execute()
