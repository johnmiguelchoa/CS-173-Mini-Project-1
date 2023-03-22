import smartpy as sp

class Lottery(sp.Contract):
    def __init__(self, _admin):
        self.init(
            players = sp.map(
                l = {},
                tkey = sp.TNat,
                tvalue = sp.TAddress
            ),
            ticket_cost = sp.tez(1),
            tickets_available = sp.nat(3),
            max_tickets = sp.nat(3),
            admin = _admin,
        )
    
    @sp.entry_point
    def buy_ticket(self, amount):
        # amount of tickets to buy
        sp.set_type(amount, sp.TNat)

        # We need to use a local variable because pythonic variables are only aliases.
        # Limit the amount to the number of tickets available if necessary
        amount = sp.local("amount", sp.min(amount, self.data.tickets_available))
        
        # Sanity checks
        # sp.verify(self.data.tickets_available >= amount, "NOT ENOUGH TICKETS AVAILABLE")
        sp.verify(sp.utils.mutez_to_nat(sp.amount) >= sp.utils.mutez_to_nat(self.data.ticket_cost) * amount.value, "NOT ENOUGH TEZ")

        # Storage updates
        sp.for i in sp.range(0, amount.value):
            self.data.players[sp.len(self.data.players)] = sp.sender
        self.data.tickets_available = sp.as_nat(self.data.tickets_available - amount.value)

        # Return extra tez balance to the sender
        extra_balance = sp.as_nat(sp.utils.mutez_to_nat(sp.amount) - sp.utils.mutez_to_nat(self.data.ticket_cost) * amount.value)
        sp.if extra_balance > 0:
            sp.send(sp.sender, sp.utils.nat_to_mutez(extra_balance))

    @sp.entry_point
    def end_game(self, random_number):
        sp.set_type(random_number, sp.TNat)

        # Sanity checks
        sp.verify(sp.sender == self.data.admin, "NOT AUTHORISED")
        sp.verify(self.data.tickets_available == 0, "GAME IS YET TO END")

        # Pick a winner
        winner_id = random_number % self.data.max_tickets
        winner_address = self.data.players[winner_id]

        # Send the reward to the winner
        sp.send(winner_address, sp.balance)

        # Reset the game
        self.data.players = {}
        self.data.tickets_available = self.data.max_tickets

    @sp.entry_point
    def change_variables(self, ticket_cost, max_tickets):
        sp.set_type(ticket_cost, sp.TMutez)
        sp.set_type(max_tickets, sp.TNat)

        sp.verify(sp.sender == self.data.admin, "NOT AUTHORISED")
        sp.verify(self.data.tickets_available == self.data.max_tickets, "A GAME IS STILL ON (1)")
        sp.verify(sp.len(self.data.players) == 0, "A GAME IS STILL ON (2)")
        # sp.verify(sp.balance == sp.tez(0), "A GAME IS STILL ON (3)")

        self.data.ticket_cost = ticket_cost
        self.data.max_tickets = max_tickets
        self.data.tickets_available = max_tickets

    @sp.entry_point
    def change_ticket_cost(self, ticket_cost):
        sp.set_type(ticket_cost, sp.TMutez)

        sp.verify(sp.sender == self.data.admin, "NOT AUTHORISED")
        sp.verify(self.data.tickets_available == self.data.max_tickets, "A GAME IS STILL ON (1)")
        sp.verify(sp.len(self.data.players) == 0, "A GAME IS STILL ON (2)")
        # sp.verify(sp.balance == sp.tez(0), "A GAME IS STILL ON (3)")

        self.data.ticket_cost = ticket_cost

    @sp.entry_point
    def change_max_tickets(self, max_tickets):
        sp.set_type(max_tickets, sp.TNat)

        sp.verify(sp.sender == self.data.admin, "NOT AUTHORISED")
        sp.verify(self.data.tickets_available == self.data.max_tickets, "A GAME IS STILL ON (1)")
        sp.verify(sp.len(self.data.players) == 0, "A GAME IS STILL ON (2)")
        # sp.verify(sp.balance == sp.tez(0), "A GAME IS STILL ON (3)")

        self.data.max_tickets = max_tickets
        self.data.tickets_available = max_tickets
    
    @sp.entry_point
    def default(self):
        sp.failwith("NOT ALLOWED")

@sp.add_test(name = "main")
def test():
    scenario = sp.test_scenario()

    # Test accounts
    admin = sp.test_account("admin")
    alice = sp.test_account("alice")
    bob = sp.test_account("bob")
    mike = sp.test_account("mike")

    # Contract instance
    lottery = Lottery(admin.address)
    scenario += lottery

    # TEST 1: Each person tries to buy 2 tickets each
    scenario.h2("TEST 1: Each person tries to buy 2 tickets each")
    scenario += lottery.buy_ticket(2).run(amount = sp.tez(2), sender = alice)
    scenario += lottery.buy_ticket(2).run(amount = sp.tez(2), sender = bob)
    scenario += lottery.buy_ticket(2).run(amount = sp.tez(2), sender = mike)
    scenario += lottery.end_game(3).run(sender = admin)

    # TEST 2: Admin changes the variables
    scenario.h2("TEST 2: Admin changes the variables")
    scenario += lottery.change_ticket_cost(sp.tez(3)).run(sender = admin)
    scenario += lottery.change_max_tickets(sp.nat(9)).run(sender = admin)
    scenario += lottery.change_variables(ticket_cost = sp.tez(2), max_tickets = sp.nat(5)).run(sender = admin)

    # TEST 3: Non-admin tries to change variables
    scenario.h2("TEST 3: Non-admin tries to change variables")
    scenario += lottery.change_ticket_cost(sp.tez(10)).run(sender = alice, valid = False)
    scenario += lottery.change_max_tickets(sp.nat(10)).run(sender = bob, valid = False)
    scenario += lottery.change_variables(ticket_cost = sp.tez(10), max_tickets = sp.nat(10)).run(sender = mike, valid = False)

    # TEST 4: Admin tries to change variables while a game is on
    scenario.h2("TEST 4: Admin tries to change variables while a game is on")
    scenario += lottery.buy_ticket(2).run(amount = sp.tez(4), sender = alice)
    scenario += lottery.change_ticket_cost(sp.tez(5)).run(sender = admin, valid = False)
    scenario += lottery.change_max_tickets(sp.nat(10)).run(sender = admin, valid = False)
    scenario += lottery.change_variables(ticket_cost = sp.tez(5), max_tickets = sp.nat(10)).run(sender = admin, valid = False)