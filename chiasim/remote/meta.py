
def make_proxy(make_invocation_f, context=None):

    class Proxy:
        @classmethod
        def __getattribute__(self, attr_name):
            def invoke(*args, **kwargs):
                return make_invocation_f(attr_name, context, *args, **kwargs)
            return invoke

    return Proxy()
