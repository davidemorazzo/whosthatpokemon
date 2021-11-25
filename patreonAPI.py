import patreon

#Versione API:2
# ACCESS_TOKEN = "pskTwhilaLvThYGConYs0go1J_s7BrcyCDqX3xdn9bw"
AC_TOKEN = "AEvOwWqKgxLyQ4CR27erNQlCkaJcMZC8WKiE2IrJOBQ"

#TODO make this async
def fetch_patreons(ACCESS_TOKEN) -> dict:
    api_client = patreon.API(ACCESS_TOKEN)

    # Get the campaign ID
    campaign_response = api_client.fetch_campaign()
    campaign_id = campaign_response.data()[0].id()

    # Fetch all pledges
    all_pledges = []
    cursor = None
    while True:
        pledges_response = api_client.fetch_page_of_pledges(campaign_id, 25, cursor=cursor)
        all_pledges += pledges_response.data()
        cursor = api_client.extract_cursor(pledges_response)
        if not cursor:
            break
    # FINO A QUI PRESO DAI DOCS
    
    ## => LIST OF ACTIVE USERS
    active_user_dict = {}
    for pledge in all_pledges:
        declined = pledge.attribute('declined_since')
        member = pledge.relationship('patron')
        discord_id = member.attribute('social_connections')['discord']
        reward_tier = str(pledge.relationship('reward').attribute('amount_cents'))

        if discord_id != None:
            active_user_dict[discord_id['user_id']] = [str(declined), reward_tier]
    
    return active_user_dict


if __name__ == '__main__':
    DICT = fetch_patreons(AC_TOKEN)
    print(DICT)