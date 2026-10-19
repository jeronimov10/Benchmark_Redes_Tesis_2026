"""Hashes keccak256 para derivar topics de eventos y selectores de funciones a partir de su firma (nunca copiados de memoria)."""

from Crypto.Hash import keccak


def keccak256_hex(texto):
    k = keccak.new(digest_bits=256)
    k.update(texto.encode())
    return k.hexdigest()


def topic(firma):
    return "0x" + keccak256_hex(firma)


def selector(firma):
    return "0x" + keccak256_hex(firma)[:8]
