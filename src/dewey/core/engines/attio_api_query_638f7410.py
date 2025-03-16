```python
import requests


def make_attio_request(url: str, headers: dict) -> str:
    """Makes a POST request to the Attio API and returns the response text.

    Args:
        url: The URL of the Attio API endpoint.
        headers: A dictionary containing the request headers.

    Returns:
        The text content of the response.
    """
    response = requests.post(url, headers=headers)
    return response.text


def main() -> None:
    """Main function to execute the Attio API request and print the response."""
    url: str = "https://api.attio.com/v2/objects/people/records/query"

    headers: dict = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": "Bearer db05495d98ca3364876e4070fd3acf4510f4d0c5b85f0b353944e4cf94385544",
    }

    response_text: str = make_attio_request(url, headers)
    print(response_text)


if __name__ == "__main__":
    main()
```
