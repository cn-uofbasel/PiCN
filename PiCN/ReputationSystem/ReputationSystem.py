#manage reputation for all service providers


from PiCN.ReputationSystem.Reputation import Reputation
import inspect


class reputationSystem:

    def __init__(self):
        self.knownEntitys = []
        self.trustFullyVallue=95

    def addNewEntity(self, keyName, ip, port, name = None, reputation=None, nc=None, pc=None):
        self.knownEntitys.append(Reputation(keyName, ip, port, name, reputation, nc, pc))

    def print(self):
        #for x in range(len(self.knownEntitys)):
        for rep in self.knownEntitys:

            if isinstance(rep, type(Reputation("1","1","1"))):
                rep.printNice()
            else:
                print("Error, not type reputation")
                print(rep)

    def searchEntitybyName(self, name):
        for i in range(len(self.knownEntitys)):
            if self.knownEntitys[i].name == name:
                return i
        return -1

    def searchEntity(self, keyID):
        for i in range(len(self.knownEntitys)):
            if self.knownEntitys[i].id == keyID:
                return i
        return -1

    def searchName(self, name):
        for i in range(len(self.knownEntitys)):
            if self.knownEntitys[i].name == name:
                return i
        return -1

    def updateReputation(self, keyID, rating, ip, port, name = None, nc=None, pc=None):
        #rating can be +1 or -1 (for now)
        index = self.searchEntity(keyID)

        if index < 0:
            # index not found add it, should not be used
            self.addNewEntity(keyID, ip, port, name=name,nc=nc,pc=pc)

        if rating >= 0:
            self.knownEntitys[index].ratePositive()
        else:
            self.knownEntitys[index].rateNegative()

    def getBestEntity(self):
        if len(self.knownEntitys)<=0:
            return -1
        best = 0
        index = 0
        for i in range(len(self.knownEntitys)):
            if self.calcScoreforEntity(i)>best:
                best=self.calcScoreforEntity(i)
                index=i
        return self.knownEntitys[index]
        #old todo what to do with this?
        candidate = self.getHigestReputationEntity()
        maxpositive= self.getHigestPositiveCounterEntity()
        #if candidate has hig reputation and no negative and relativle amny gud results
        if candidate.negativeCounter == 0 and maxpositive.positiveCounter-candidate.positiveCounter < maxpositive.positiveCounter/2:
            return candidate
        #return higest positive counter if reputation is not to low and positive counter is much higer
        if candidate.reputation/maxpositive.reputation < 1.05 and maxpositive.positiveCounter-candidate.positiveCounter > maxpositive.positiveCounter/2:
            return maxpositive

    def calcScoreforEntity(self, index):
        if self.knownEntitys[index].reputation:
            return self.knownEntitys[index].reputation*self.knownEntitys[index].positiveCounter -self.knownEntitys[index].negativeCounter*20
        else:
            return 0

    def getHigestPositiveCounterEntity(self):
        best = 0
        index = 0
        if len(self.knownEntitys) <= 0:
            return -1

        for i in range(len(self.knownEntitys)):
            if self.knownEntitys[i].positiveCounter > best and self.knownEntitys[i].ip !=0:
                index = i
                best = self.knownEntitys[i].positiveCounter
        return self.knownEntitys[index]

    def getHigestReputationEntity(self):
        #retruns Reputation of entity wit best reputation, -1 if empty
        best = 0
        index = 0
        if len(self.knownEntitys) <=0:
            return -1

        for i in range(len(self.knownEntitys)):
            if self.knownEntitys[i].reputation > best and self.knownEntitys[i].ip !=0:
                index = i
                best = self.knownEntitys[i].reputation


        print("node with best reputation is:")
        self.printReputation(self.knownEntitys[index])

        return self.knownEntitys[index]

    def printReputation(self, rep):
        print("key name :", rep.id, end="")
        print(" reputation :", rep.reputation, end="")
        print(" positive :", rep.positiveCounter, end="")
        print(" negative :", rep.negativeCounter)


    def __bytes__(self):
        #print("to bytes reput syst")
        arr = b""
        for i in range(len(self.knownEntitys)):
            #print("loop", i)
            #print(self.knownEntitys[i].name)
            arr += b"#?#"
            arr += self.knownEntitys[i].__bytes__()
            arr += b"#?#"
        return arr

    def updateReputationwithForeignInfo(self,index, keyID, rating, ip, port, name = None, nc=None, pc=None):
        #index = self.searchEntity(keyID)
        #print("update reputation foreign")
        if index < 0:
            # index not found add it, should not be used
            self.addNewEntity(keyID, ip, port, name=name,reputation=rating,nc= nc, pc=pc)
            return

        #print(rating)
        #print(self.knownEntitys[index].reputation)
        #todo weight avg with nc, pc
        #if positiv reting is bether than current
        if rating > 0 and self.knownEntitys[index].reputation-rating < 0:

            ownpc=self.knownEntitys[index].positiveCounter
            self.knownEntitys[index].reputation = min(float((self.knownEntitys[index].reputation*ownpc+rating*pc)/(ownpc+pc)),rating)
            #print("positiv reting is bether")
            #print((self.knownEntitys[index].reputation*ownpc+rating*pc)/(ownpc+pc))
        #if negative rating is bader than current
        elif rating <= 0 and self.knownEntitys[index].reputation-rating > 0:
            ownnc = self.knownEntitys[index].negativeCounter

            self.knownEntitys[index].reputation = max(float((self.knownEntitys[index].reputation*ownnc+rating*nc)/(ownnc+nc)),rating)
            #print("negative rating is bader")

        #todo rating is between 0 and current
        else:
            pass
            #print("else!")