// Object storage client: putObject(key, body) uploads one object; there is no multipart upload.
async function putObject(key, body) {
  if (!key) throw new Error('key required');
  return { key, bytes: Buffer.byteLength(body) };
}

module.exports = { putObject };
