from discord import ext, app_commands

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from os import urandom
from base64 import b64encode, b64decode
from secrets import token_bytes


class AES(ext.commands.Cog):
   def __init__(self, bot):
       self.bot = bot

   @ext.commands.hybrid_command()
   @app_commands.allowed_contexts(True, True, True)
   async def aes_encrypt(self, ctx: ext.commands.Context, *, text: str):
       key = urandom(256 // 8)
       iv = urandom(96 // 8)

       text = text.encode()
       asso = token_bytes(64)

       aesgcm_encryptor = Cipher(algorithms.AES(key), modes.GCM(iv)).encryptor()
       aesgcm_encryptor.authenticate_additional_data(asso)
       ciphertext = aesgcm_encryptor.update(text) + aesgcm_encryptor.finalize()
       tag = aesgcm_encryptor.tag

       aesgcm_decryptor = Cipher(algorithms.AES(key), modes.GCM(iv, tag)).decryptor()
       aesgcm_decryptor.authenticate_additional_data(asso)
       recovered_text = aesgcm_decryptor.update(ciphertext) + aesgcm_decryptor.finalize()

       assert (recovered_text == text)

       await ctx.send(
           f"""Encrypted text: ```{b64encode(ciphertext).decode()}```\nKey: ```{b64encode(key).decode()}```\nIv: ```{b64encode(iv).decode()}```\nAssociated Data: ```{b64encode(asso).decode()}```\nTag: ```{b64encode(tag).decode()}```""",
           ephemeral=True)

   @ext.commands.hybrid_command()
   @app_commands.allowed_contexts(True, True, True)
   async def aes_decrypt(self, ctx: ext.commands.Context, ciphertext: str, key: str, iv: str, asso: str, *, tag: str):
       aesgcm_decryptor = Cipher(algorithms.AES(b64decode(key)), modes.GCM(b64decode(iv), b64decode(tag))).decryptor()
       aesgcm_decryptor.authenticate_additional_data(b64decode(asso))
       recovered_text = aesgcm_decryptor.update(b64decode(ciphertext)) + aesgcm_decryptor.finalize()
       await ctx.send(f"""Text: {recovered_text.decode()}""")

async def setup(bot):
    await bot.add_cog(AES(bot))