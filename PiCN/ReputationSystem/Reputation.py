
class Reputation(object):
    # stores the Reputation counter for a entity
    # id is name of public key
    # for easy lookup store also name prefix

    # todo is ip port realy needed?

    def __init__(self, keyName, ip, port, name = None, reputation= None , nc=0, pc=0):
        self.id = keyName
        self.name = name
        if type(reputation )== type(None):

            self.reputation = 50
        else:

            self.reputation = reputation

        if nc==0 or type(reputation )== type(None):

            self.negativeCounter = 0
        else:
            self.negativeCounter = nc

        if pc == 0 or type(reputation )== type(None):
            self.positiveCounter = 0
        else:
            self.positiveCounter = pc

        # self.negativeCounter = int(nc)
        # self.positiveCounter = int(pc)
        self.ip = ip
        self.port =port
        self.provenanceRecords = []

    def ratePositive(self):
        if type(self.reputation )== type(None):
            self.reputation = 50
        else:
            self.reputation = max (( (self.reputation *2 + 100) / 3 - self.negativeCounter), 0)
        self.positiveCounter += 1

    def rateNegative(self):
        # print(self.negativeCounter)
        # print(type(self.negativeCounter))
        # self.negativeCounter += 1
        self.negativeCounter += 1
        if type(self.reputation) == type(None):
            self.reputation = 50
        else:
            self.reputation = (self.reputation * 2 + 0) / 3
        self.reputation -= 1
        if self.reputation <= 0:
            self.reputation = 0

    # todo more complex and usfull calculation
    def updateReputation(self, newRating):
        pass

    def printNice(self):
        print("\nkeyID:           ", self.id)
        print("name:              ", self.name)
        print("negativCounter:  ", self.negativeCounter)
        print("positiveCounter: ", self.positiveCounter)
        print("Reputation:      ", self.reputation)
        print("\n")

    def __bytes__(self):
        # print(self.id)
        if self.id == None:
            return b""

        endbyte = b"#"
        b = self.id
        b += endbyte
        b += bytes(self.name, encoding='utf8')
        b += endbyte
        b += bytes(str(self.reputation), encoding='utf8')
        b += endbyte
        b += bytes(str(self.negativeCounter), encoding='utf8')
        b += endbyte
        b += bytes(str(self.positiveCounter), encoding='utf8')
        b += endbyte
        if self.ip is None:
            b += b"-1"
        else:
            b += bytes(str(self.ip), encoding='utf8')
        b += endbyte

        if self.port is None:
            b += b"-1"
        else:
            b += bytes(str(self.port), encoding='utf8')
        return b

    def niceString(self):
        if type(self.id) == type(b" "):
            id = self.id.decode('ISO-8859-1')
        else:
            id = self.id
        if type(self.name) == type(b" "):
            name = self.name.decode()
        else:
            name = self.name
        return "\nkeyID:           " + id + "\nname:             " + name + "\nnegativCounter:  " + str(
            self.negativeCounter) + "\npositiveCounter: " + str(self.positiveCounter) + "\nReputation:      " + str(
            self.reputation) + "\n"
