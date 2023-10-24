import ldap

from django.conf import settings


def get_ldap_admin_connection():
    conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
    if settings.AUTH_LDAP_START_TLS:
        conn.start_tls_s()
    conn.simple_bind_s(settings.AUTH_LDAP_BIND_DN, settings.AUTH_LDAP_BIND_PASSWORD)
    return conn


def get_ldap_user_connection(user_dn, password):
    conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
    if settings.AUTH_LDAP_START_TLS:
        conn.start_tls_s()
    conn.simple_bind_s(user_dn, password)
    return conn
