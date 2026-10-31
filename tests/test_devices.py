from babel86 import devices


def test_mock_output_list_has_the_agreed_shape():
    outputs = devices.list_outputs()
    assert [(d.name, d.channels) for d in outputs] == [("Speakers", 2), ("Interpreter Desk", 8)]
    assert len({d.id for d in outputs}) == len(outputs)


def test_find_and_route_name():
    assert devices.find("mock:speakers").channels == 2
    assert devices.find("nope") is None
    assert devices.route_name("mock:speakers", "Old name") == "Speakers"  # the live name wins
    assert devices.route_name("usb:gone", "Desk 2") == "Desk 2 (disconnected)"
    assert devices.route_name("usb:gone", "") == "usb:gone (disconnected)"
