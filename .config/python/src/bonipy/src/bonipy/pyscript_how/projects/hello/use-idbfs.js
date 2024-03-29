import plainTag from 'https://esm.sh/plain-tag';
import { loadPyodide } from 'https://cdn.jsdelivr.net/pyodide/v0.23.4/full/pyodide.mjs';

content.textContent = 'loading pyodide ...';
const { FS, runPython } = await loadPyodide();
content.textContent = '';

const py = (...args) => runPython(plainTag(...args));

// mount the IDBFS folder
const mountDir = "/mnt";
FS.mkdir(mountDir);
FS.mount(FS.filesystems.IDBFS, { root: "." }, mountDir);
FS.syncfs(true, error => {
  if (error) throw error;
  read();
});
py`import sys;sys.path.append("${mountDir}")`;

const read = () => {
  py`
    from js import document
    import os
    import sys

    document.getElementById("content").textContent = "\\n".join(os.listdir("${mountDir}"))
  `;
};

write.disabled = false;
write.addEventListener('click', event => {
  event.preventDefault();
  const content = prompt('What would you like to write?');
  if (content) {
    FS.writeFile(`${mountDir}/file_${+new Date}.txt`, content);
    FS.syncfs(error => {
      if (error) throw error;
    });
    read();
  }
});
