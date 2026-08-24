// Small shared DOM/array helpers used across the practice, review,
// mock-exam and upload pages.

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === 'class') node.className = v;
    else if (k === 'html') node.innerHTML = v;
    else node.setAttribute(k, v);
  });
  (Array.isArray(children) ? children : [children]).forEach(c => {
    if (c) node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  });
  return node;
}

function uniq(arr) { return [...new Set(arr)]; }

function fillSelect(sel, values, placeholder, labelMap) {
  sel.innerHTML = `<option value="">${placeholder}</option>` +
    values.map(v => `<option value="${v}">${labelMap ? localizedLabel(v, labelMap) : v}</option>`).join('');
}
