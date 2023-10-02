## Coding style guide

We follow [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/), PEP 257 – Docstring Conventions(https://peps.python.org/pep-0257/). Please read it carefully before submitting a merge request.

- All comments should be written in English.
- Strings should be single-quoated. However, when a string contains single quote characters, you can use double quotes to avoid blackslashes in the string.
- For triple-quoted strings, always use double quote characters to be consistent with the docstring convention in [PEP 257](https://peps.python.org/pep-0257/).

### Import rules

Imports should be grouped in the following order:

1. Standard library imports
2. Django libary imports
3. Related third party imports
4. Local application/library specific imports

Absolute imports are recommended. For example `from servers.models import Server` is preferred than `from .models import Server`.

Wildcard imports such as `from servers.models import *` should be avoided. Rather, all imports should be made explicitly such as the followings. Line breaks can be made if it exceeds 72 characters.

```python
from servers.api.serializers import (
    ServerSerializer, ServerDetailSerializer,
    ServerCreateSerializer, ServerUpdateSerializer,
)
```

Do not import settings directly from `alpacon/settings.py`. Instead, use django settings module to read values.

NOT ALLOWED:

```python
from alpacon.settings import USE_LDAP_AUTH_BACKEND

print(USE_LDAP_AUTH_BACKEND)
```

CORRECT:

```python
from django.conf import settings

print(settings.USE_LDAP_AUTH_BACKEND)
```
