import logging

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status, Request
from ldap3 import Server, Connection, ALL, NTLM, SIMPLE

from src.utils import get_config

SECRET_KEY = "Iuyz0aHP7onomD71BtbcO+DRpnUzLs7KJCpYJ6jPLLc=" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8

# LDAP Configuration
LDAP_BASE_DN = "ou=users,dc=nitro,dc=com"
LDAP_USER_DN_TEMPLATE = "uid={},ou=users,dc=nitro,dc=com"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate user against LDAP server and verify group membership.
    Returns user info dict if successful and in required group, None otherwise.
    """
    user_dn = LDAP_USER_DN_TEMPLATE.format(username)

    conf = get_config()

    server = Server(conf.LDAP_SERVER, port=conf.LDAP_PORT, get_info=ALL)

    try:
        # Bind with user credentials to verify password
        conn = Connection(server, user=user_dn, password=password, authentication=SIMPLE)
        if not conn.bind():
            logging.warning(f"LDAP bind failed for user: {username}")
            return None

        # Search for user and fetch memberOf attribute
        conn.search(
            search_base=LDAP_BASE_DN,
            search_filter=f"(uid={username})",
            attributes=['cn', 'mail', 'givenName', 'sn', 'memberOf']
        )

        if len(conn.entries) == 0:
            logging.warning(f"No LDAP entry found for user: {username}")
            conn.unbind()
            return None

        entry = conn.entries[0]

        # Check group membership
        required_group = "cn=chat-users,ou=groups,dc=nitro,dc=com"
        member_of = getattr(entry, 'memberOf', [])
        if isinstance(member_of, str):
            member_of = [member_of]  # In case only one group is returned as string

        if required_group not in member_of:
            logging.warning(f"User {username} is not a member of required group: {required_group}")
            conn.unbind()
            return None


        # Return user info (JWT will be issued after this)
        user = {
            "username": username,
            "groups": member_of.values,
        }

        conn.unbind()
        return user

    except Exception as e:
        logging.error(f"LDAP authentication error for {username}: {e}")
        return None

async def get_current_user(request: Request):
    """Extract and validate JWT from HTTP-only cookie"""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    
    user = {
        "username": username,
        "groups": payload.get('groups')
    }
    return user