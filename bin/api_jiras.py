import splunk.admin as admin
import splunk.entity as en
import sys

class JirasConfigApp(admin.MConfigHandler):

    """Set up supported arguments"""

    def setup(self):
        if self.requestedAction in [admin.ACTION_EDIT, admin.ACTION_CREATE]:
            self.supportedArgs.addOptArg('*')

    def handleCreate(self, confInfo):
        # args comes back as a list of items, rather than just the items
        self.handleEdit(confInfo)

    def handleList(self, confInfo):
        config = self.readConf("jiras")
        if config is None:
            return

        for stanza, settings in config.iteritems():
            for name, value in settings.items():
                value_ = value if value is not None else ""
                confInfo[stanza][name] = value_

    def handleEdit(self, confInfo):
        stanza = self.callerArgs.id
        args = self.callerArgs

        # args comes back as a list of items, rather than just the items
        for item_name, value in args.data.items():
            assert len(value) == 1
            value = value[0]
            args.data[item_name] = value if value is not None else ""
        self.writeConf("jiras", stanza, args.data)


# initialize the handler
admin.init(JirasConfigApp, admin.CONTEXT_NONE)
