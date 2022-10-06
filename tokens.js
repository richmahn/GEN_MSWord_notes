const deepcopy = require('deepcopy');

const slimSourceTokens = (tokens) => {
    const ret = [];
    const occurrences = {};
    if (!tokens) {
        return null;
    }
    for (const token of tokens) {
        const t2 = deepcopy(token);
        t2.payload = t2.payload.replace(/[ \t\r\n]+/g, " ");
            if (!(t2.payload in occurrences)) {
                occurrences[t2.payload] = 1;
            } else {
                occurrences[t2.payload]++;
            }
            t2.occurrence = occurrences[t2.payload];
        delete t2.scopes;
        ret.push(t2);
    }
    return ret;
}

const slimGLTokens = (tokens) => {
    const ret = [];
    if (!tokens) {
        return null;
    }
    for (const token of tokens) {
        const t2 = deepcopy(token);
        const occurrenceScopes = t2.scopes.filter(s => s.startsWith("attribute/milestone/zaln/x-occurrence") && !s.endsWith("s"));
        const xContentScopes = t2.scopes.filter(s => s.startsWith("attribute/milestone/zaln/x-content"));
        t2.blContent = xContentScopes.map(s => s.split("/")[5]);
        t2.payload = t2.payload.replace(/[ \t\r\n]+/g, " ");
        t2.occurrence = occurrenceScopes.map(o => parseInt(o.split("/")[5]));
        delete t2.scopes;
        ret.push(t2);
    }
    return ret;
}

const pruneTokens = tokens => {

    const pruneStart = ts => {
        if (ts.length === 0 || ts[0][1]) {
            return ts;
        } else {
            return pruneStart(ts.slice(1));
        }
    }

    const pruneEnd = ts => {
        if (ts.length === 0 || ts[ts.length - 1][1]) {
            return ts;
        } else {
            return pruneEnd(ts.slice(0, ts.length - 1));
        }
    }

    return pruneEnd(pruneStart(tokens));

}

module.exports = {slimSourceTokens, slimGLTokens, pruneTokens};
