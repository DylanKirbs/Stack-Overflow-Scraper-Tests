from difflib import SequenceMatcher


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


print(similar(
    r"<p>I have strange error when I decided to build ordinary web-form validation with classic javascript. There are several \"onblur\" handlers for input text fields and one \"form-submit\" handler. </p>\n<p>When I use them like that:</p>\n<pre><code>function loginCheck() {\n  ... return true of false \n}\n\nfunction passwordCheck() { \n   ...\n}\n\nfunction formValidation() {\n  return loginCheck() &amp;&amp; passwordCheck();\n}\n</code></pre>\n<p>It doesn't work as I expect: \"passwordCheck\" never called if loginCheck is failed! </p>\n<p>Finally I have workaround </p>\n<pre><code>function formValidation() {\n  ok = loginCheck();\n  ok &amp;= passwordCheck();\n  return ok;\n}\n</code></pre>\n<p>Now password check is executed. But when I choose:</p>\n<pre><code>function formValidation() {\n      ok = loginCheck();\n      ok = ok &amp;&amp; passwordCheck();\n      return ok;\n    }\n</code></pre>\n<p>passwordCheck is never called again if loginCheck failed. </p>\n<p>Moreover: loginCheck &amp; passwordCheck return boolean values, but &amp;= operator covert it to \"0\" or \"1\". \"0\" doesn't work for my <code>onsubmit=&quot;return checkForm&quot;</code> handler.   I have to convert my &amp;= result to boolean once again:</p>\n<pre><code>function formValidation() {\n      ok = loginCheck();\n      ok &amp;= passwordCheck();\n      return ok != 0;\n    }\n</code></pre>\n<p>It is a normal behavior for javascript engines ? </p>\n",
    r"<p>I have strange error when I decided to build ordinary web-form validation with classic javascript. There are several \"onblur\" handlers for input text fields and one \"form-submit\" handler. </p>\n\n<p>When I use them like that:</p>\n\n<pre><code>function loginCheck() {\n  ... return true of false \n}\n\nfunction passwordCheck() { \n   ...\n}\n\nfunction formValidation() {\n  return loginCheck() &amp;&amp; passwordCheck();\n}\n</code></pre>\n\n<p>It doesn't work as I expect: \"passwordCheck\" never called if loginCheck is failed! </p>\n\n<p>Finally I have workaround </p>\n\n<pre><code>function formValidation() {\n  ok = loginCheck();\n  ok &amp;= passwordCheck();\n  return ok;\n}\n</code></pre>\n\n<p>Now password check is executed. But when I choose:</p>\n\n<pre><code>function formValidation() {\n      ok = loginCheck();\n      ok = ok &amp;&amp; passwordCheck();\n      return ok;\n    }\n</code></pre>\n\n<p>passwordCheck is never called again if loginCheck failed. </p>\n\n<p>Moreover: loginCheck &amp; passwordCheck return boolean values, but &amp;= operator covert it to \"0\" or \"1\". \"0\" doesn't work for my <code>onsubmit=\"return checkForm\"</code> handler.   I have to convert my &amp;= result to boolean once again:</p>\n\n<pre><code>function formValidation() {\n      ok = loginCheck();\n      ok &amp;= passwordCheck();\n      return ok != 0;\n    }\n</code></pre>\n\n<p>It is a normal behavior for javascript engines ? </p>\n"
))