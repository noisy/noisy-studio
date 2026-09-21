const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

for (const [name, profile] of [
  ['Noisy Studio', 'Noisy Studio'],
  ['Noisy Studio Dev', 'Noisy Studio Dev'],
]) {
  test(`${name} selects its canonical profile before Electron becomes ready`, () => {
    const configuredPaths = {};
    const app = {
      getName: () => name,
      getPath: key => { assert.equal(key, 'appData'); return '/application-data'; },
      setPath: (key, value) => { configuredPaths[key] = value; },
      whenReady: () => {
        assert.deepEqual(configuredPaths, { userData: `/application-data/${profile}` });
        return { then() {} };
      },
      on() {},
    };
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, 'main.js'), 'utf8'), {
      require: id => id === 'electron' ? { app } : require(id),
      process: { env: {} },
      __dirname,
    });
  });
}
